using System.Collections.Concurrent;
using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public sealed class InMemoryViolationEventService : IViolationEventService
{
    private readonly ConcurrentQueue<ViolationRecord> _records = new();
    private readonly ILogger<InMemoryViolationEventService> _logger;
    private readonly int _maxItems;

    public InMemoryViolationEventService(
        IConfiguration configuration,
        ILogger<InMemoryViolationEventService> logger)
    {
        _logger = logger;
        _maxItems = Math.Clamp(configuration.GetValue("ViolationStore:MaxItems", 1000), 100, 10_000);
    }

    public ViolationRecord Record(ViolationEventRequest request)
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

        _logger.LogInformation(
            "Violation accepted. EventType={EventType} CameraId={CameraId} SiteId={SiteId} TrackId={TrackId} Confidence={Confidence}",
            request.EventType,
            request.CameraId,
            request.SiteId,
            request.TrackId,
            request.Confidence);

        return record;
    }

    public IReadOnlyCollection<ViolationRecord> GetRecent(int limit = 50)
    {
        var boundedLimit = Math.Clamp(limit, 1, 500);
        return _records.Reverse().Take(boundedLimit).ToArray();
    }
}
