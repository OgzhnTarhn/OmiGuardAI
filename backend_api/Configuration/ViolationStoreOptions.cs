namespace OmniGuard.BackendApi.Configuration;

public sealed class ViolationStoreOptions
{
    public int MaxItems { get; init; } = 1000;

    public string DataDirectory { get; init; } = "data";

    public string FileName { get; init; } = "violations.ndjson";
}
