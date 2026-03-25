namespace OmniGuard.BackendApi.Configuration;

public sealed class TelegramOptions
{
    public bool Enabled { get; init; }

    public string BotToken { get; init; } = string.Empty;

    public string ChatId { get; init; } = string.Empty;
}
