using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public interface IViolationEventService
{
    ViolationRecord Record(ViolationEventRequest request);

    IReadOnlyCollection<ViolationRecord> GetRecent(int limit = 50);
}
