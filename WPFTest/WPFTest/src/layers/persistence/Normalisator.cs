using System;
using Newtonsoft.Json;
using namespace.persistence

//Datamodel for Messages for Normalisator
//Gemaakt door J.C.G van den Hurk
//Datum: 13-4-2026 - 23-4-2026

//Scope: De JSON export van Discord bevat veel informatie, maar de gestelde eisen na aanleiding van het bezoek op het hoofdbureau is de prioriteit alleen om Private Messages te exporteren.
//Dit Data model is gemaakt om de relevante informatie uit de JSON export van Discord te halen en deze te normaliseren zodat deze gebruikt kan worden voor het genereren van een PDF rapportage.

namespace Layers.Persistence.Models
{
    // De root van de JSON export
    internal class DiscordExport
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

    // De server/guild info
    internal class DiscordGuild
    {
        [JsonProperty("id")]
        public string? Id { get; set; }

        [JsonProperty("name")]
        public string? Name { get; set; }

        [JsonProperty("iconUrl")]
        public string? IconUrl { get; set; }
    }

    // Het kanaal waar de berichten uit komen
    internal class DiscordChannel
    {
        [JsonProperty("id")]
        public string? Id { get; set; }

        [JsonProperty("type")]
        public string? Type { get; set; }

        [JsonProperty("name")]
        public string? Name { get; set; }
    }

    // Een enkel bericht
    internal class DiscordMessage
    {
        [JsonProperty("id")]
        public string? Id { get; set; }

        [JsonProperty("type")]
        public string? Type { get; set; }

        [JsonProperty("timestamp")]
        public DateTime Timestamp { get; set; }

        [JsonProperty("timestampEdited")]
        public DateTime? TimestampEdited { get; set; }

        [JsonProperty("isPinned")]
        public bool IsPinned { get; set; }

        [JsonProperty("content")]
        public string? Content { get; set; }

        [JsonProperty("author")]
        public DiscordAuthor? Author { get; set; }

        [JsonProperty("attachments")]
        public List<DiscordAttachment> Attachments { get; set; } = new();

        [JsonProperty("embeds")]
        public List<DiscordEmbed> Embeds { get; set; } = new();

        [JsonProperty("stickers")]
        public List<DiscordSticker> Stickers { get; set; } = new();
    }

    // De auteur van een bericht
    internal class DiscordAuthor
    {
        [JsonProperty("id")]
        public string? Id { get; set; }

        [JsonProperty("name")]
        public string? Name { get; set; }

        [JsonProperty("nickname")]
        public string? Nickname { get; set; }

        [JsonProperty("isBot")]
        public bool IsBot { get; set; }

        [JsonProperty("avatarUrl")]
        public string? AvatarUrl { get; set; }
    }

    // Een bijlage zoals een afbeelding of bestand
    internal class DiscordAttachment
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

    // Een embed zoals een GIF of link preview
    internal class DiscordEmbed
    {
        [JsonProperty("title")]
        public string? Title { get; set; }

        [JsonProperty("url")]
        public string? Url { get; set; }

        [JsonProperty("description")]
        public string? Description { get; set; }

        [JsonProperty("thumbnail")]
        public DiscordEmbedThumbnail? Thumbnail { get; set; }
    }

    // De thumbnail van een embed
    internal class DiscordEmbedThumbnail
    {
        [JsonProperty("url")]
        public string? Url { get; set; }

        [JsonProperty("width")]
        public int Width { get; set; }

        [JsonProperty("height")]
        public int Height { get; set; }
    }

    // Een sticker
    internal class DiscordSticker
    {
        [JsonProperty("id")]
        public string? Id { get; set; }

        [JsonProperty("name")]
        public string? Name { get; set; }

        [JsonProperty("format")]
        public string? Format { get; set; }

        [JsonProperty("sourceUrl")]
        public string? SourceUrl { get; set; }
    }
}

//bronnen: voor JSONproperty, Lars & https://medium.com/@kacar7/understanding-jsonproperty-in-net-f9e0d98e3135. voor JSON file Testing https://github.com/tyrrrz/discordchatexporter