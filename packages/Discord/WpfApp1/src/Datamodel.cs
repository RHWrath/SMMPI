using System;
using System.Collections.Generic;
using Newtonsoft.Json;

public class DiscordExport
{
    [JsonProperty("guild")]
    public DiscordGuild? Guild { get; set; }

    [JsonProperty("channel")]
    public DiscordChannel? Channel { get; set; }

    [JsonProperty("exportedAt")]
    public DateTime ExportedAt { get; set; }

    [JsonProperty("messages")]
    public List<DiscordMessage> Messages { get; set; } = new();

    [JsonProperty("messageCount")]
    public int MessageCount { get; set; }
}

public class DiscordGuild
{
    [JsonProperty("id")]
    public string? Id { get; set; }

    [JsonProperty("name")]
    public string? Name { get; set; }
}

public class DiscordChannel
{
    [JsonProperty("id")]
    public string? Id { get; set; }

    [JsonProperty("type")]
    public string? Type { get; set; }

    [JsonProperty("name")]
    public string? Name { get; set; }
}

public class DiscordMessage
{
    [JsonProperty("id")]
    public string? Id { get; set; }

    [JsonProperty("timestamp")]
    public DateTime Timestamp { get; set; }

    [JsonProperty("content")]
    public string? Content { get; set; }

    [JsonProperty("author")]
    public DiscordAuthor? Author { get; set; }

    [JsonProperty("attachments")]
    public List<DiscordAttachment> Attachments { get; set; } = new();
}

public class DiscordAttachment
{
    [JsonProperty("id")]
    public string? Id { get; set; }

    [JsonProperty("url")]
    public string? Url { get; set; }

    [JsonProperty("fileName")]
    public string? FileName { get; set; }

    [JsonProperty("fileSizeBytes")]
    public long FileSizeBytes { get; set; }
}

public class DiscordAuthor
{
    [JsonProperty("id")]
    public string? Id { get; set; }

    [JsonProperty("name")]
    public string? Name { get; set; }

    [JsonProperty("nickname")]
    public string? Nickname { get; set; }

    [JsonProperty("isBot")]
    public bool IsBot { get; set; }
}