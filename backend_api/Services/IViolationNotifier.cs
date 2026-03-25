using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public interface IViolationNotifier
{
    Task NotifyAsync(ViolationRecord record, CancellationToken cancellationToken = default);
}
