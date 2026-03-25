namespace OmniGuard.BackendApi.Models;

public sealed class ViolationRecord
{
    public Guid Id { get; init; }

    public DateTimeOffset ReceivedAtUtc { get; init; }

    public ViolationEventRequest Event { get; init; } = new();
}
