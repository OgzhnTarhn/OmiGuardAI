using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public sealed class LoggingViolationNotifier(ILogger<LoggingViolationNotifier> logger) : IViolationNotifier
{
    public Task NotifyAsync(ViolationRecord record, CancellationToken cancellationToken = default)
    {
        logger.LogWarning(
            "Loss prevention alert. ViolationId={ViolationId} EventType={EventType} CameraId={CameraId} SiteId={SiteId} TrackId={TrackId}",
            record.Id,
            record.Event.EventType,
            record.Event.CameraId,
            record.Event.SiteId,
            record.Event.TrackId);

        return Task.CompletedTask;
    }
}
