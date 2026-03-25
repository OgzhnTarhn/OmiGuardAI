namespace OmniGuard.BackendApi.Models;

public sealed class CreateViolationResponse
{
    public Guid Id { get; init; }

    public string Status { get; init; } = string.Empty;

    public DateTimeOffset ReceivedAtUtc { get; init; }
}
