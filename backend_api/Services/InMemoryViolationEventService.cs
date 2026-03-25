using System.Collections.Concurrent;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;
using OmniGuard.BackendApi.Configuration;
using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public sealed class InMemoryViolationEventService : IViolationEventService
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);

    private readonly ConcurrentQueue<ViolationRecord> _records = new();
    private readonly SemaphoreSlim _fileWriteLock = new(1, 1);
    private readonly IReadOnlyCollection<IViolationNotifier> _notifiers;
    private readonly ILogger<InMemoryViolationEventService> _logger;
    private readonly int _maxItems;
    private readonly string _persistenceFilePath;

    public InMemoryViolationEventService(
        IOptions<ViolationStoreOptions> violationStoreOptions,
        IHostEnvironment hostEnvironment,
        IEnumerable<IViolationNotifier> notifiers,
        ILogger<InMemoryViolationEventService> logger)
    {
        _logger = logger;
        _notifiers = notifiers.ToArray();

        var options = violationStoreOptions.Value;
        _maxItems = Math.Clamp(options.MaxItems, 100, 10_000);

        var dataDirectory = Path.GetFullPath(Path.Combine(hostEnvironment.ContentRootPath, options.DataDirectory));
        Directory.CreateDirectory(dataDirectory);
        _persistenceFilePath = Path.Combine(dataDirectory, options.FileName);
    }

    public async Task<ViolationRecord> RecordAsync(
        ViolationEventRequest request,
        CancellationToken cancellationToken = default)
    {
        var record = new ViolationRecord
        {
            Id = Guid.NewGuid(),
            ReceivedAtUtc = DateTimeOffset.UtcNow,
            Event = request,
        };

        _records.Enqueue(record);

        while (_records.Count > _maxItems && _records.TryDequeue(out _))
        {
        }

        await PersistAsync(record, cancellationToken);

        _logger.LogInformation(
            "Violation accepted. EventType={EventType} CameraId={CameraId} SiteId={SiteId} TrackId={TrackId} Confidence={Confidence}",
            request.EventType,
            request.CameraId,
            request.SiteId,
            request.TrackId,
            request.Confidence);

        foreach (var notifier in _notifiers)
        {
            try
            {
                await notifier.NotifyAsync(record, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(
                    ex,
                    "Notifier failed for violation {ViolationId} using {NotifierType}.",
                    record.Id,
                    notifier.GetType().Name);
            }
        }

        return record;
    }

    public IReadOnlyCollection<ViolationRecord> GetRecent(int limit = 50)
    {
        var boundedLimit = Math.Clamp(limit, 1, 500);
        return _records.Reverse().Take(boundedLimit).ToArray();
    }

    private async Task PersistAsync(ViolationRecord record, CancellationToken cancellationToken)
    {
        var serializedRecord = JsonSerializer.Serialize(record, SerializerOptions) + Environment.NewLine;
        var payload = Encoding.UTF8.GetBytes(serializedRecord);

        await _fileWriteLock.WaitAsync(cancellationToken);
        try
        {
            await using var stream = new FileStream(
                _persistenceFilePath,
                FileMode.Append,
                FileAccess.Write,
                FileShare.Read,
                4096,
                useAsync: true);

            await stream.WriteAsync(payload, cancellationToken);
        }
        finally
        {
            _fileWriteLock.Release();
        }
    }
}
