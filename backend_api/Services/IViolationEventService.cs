using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public interface IViolationEventService
{
    Task<ViolationRecord> RecordAsync(
        ViolationEventRequest request,
        CancellationToken cancellationToken = default);

    IReadOnlyCollection<ViolationRecord> GetRecent(int limit = 50);
}
