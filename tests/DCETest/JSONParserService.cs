using Newtonsoft.Json;

public static class JsonParserService
{
    // Deserialiseert ruwe JSON naar het DiscordExport datamodel.
    public static DiscordExport? DeserializeDiscordExport(string rawJson)
    {
        return JsonConvert.DeserializeObject<DiscordExport>(rawJson);
    }

    // Controleert of de export berichten bevat.
    public static bool HasMessages(DiscordExport? export)
    {
        return export != null &&
               export.Messages != null &&
               export.Messages.Count > 0;
    }

    // Haalt de auteur op met fallback-logica.
    public static string GetAuthorName(DiscordMessage message)
    {
        return message.Author?.Nickname
               ?? message.Author?.Name
               ?? "Onbekende auteur";
    }

    // Haalt content op met fallback voor lege berichten.
    public static string GetContent(DiscordMessage message)
    {
        return string.IsNullOrWhiteSpace(message.Content)
            ? "[Geen tekst]"
            : message.Content;
    }
}