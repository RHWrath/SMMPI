using Newtonsoft.Json;
using QuestPDF.Infrastructure;
using System;
using System.IO;
using System.IO.Pipes;
using System.Linq;

public static class JSONParser
{
    public static async Task ParseJSON(string file)
    {
        QuestPDF.Settings.License = LicenseType.Community;

        string rawJson = File.ReadAllText(file);

        if (string.IsNullOrWhiteSpace(rawJson))
        {
            Console.WriteLine("[FAIL] JSON-bestand is leeg.");
            return;
        }

        Console.WriteLine("[PASS] JSON-bestand is ingelezen.");

        DiscordExport? export;

        try
        {
            export = JsonConvert.DeserializeObject<DiscordExport>(rawJson);
        }
        catch (Newtonsoft.Json.JsonException ex)
        {
            Console.WriteLine($"[FAIL] Ongeldige JSON: {ex.Message}");
            return;
        }

        if (export == null || export.Messages.Count == 0)
        {
            Console.WriteLine("[FAIL] Geen berichten gevonden in export.");
            return;
        }

        Console.WriteLine("[PASS] JSON succesvol omgezet naar datamodel.");
        Console.WriteLine($"[PASS] Aantal berichten: {export.Messages.Count}");
        Console.WriteLine();

        foreach (var message in export.Messages)
        {
            string author = message.Author?.Nickname
                            ?? message.Author?.Name
                            ?? "Onbekende auteur";

            string content = string.IsNullOrWhiteSpace(message.Content)
                ? "[Geen tekst]"
                : message.Content;

            Console.WriteLine($"[{message.Timestamp:yyyy-MM-dd HH:mm:ss}] {author}: {content}");

            // Attachments uitlezen
            if (message.Attachments != null && message.Attachments.Count > 0)
            {
                foreach (var attachment in message.Attachments)
                {
                    string fileName = attachment.FileName ?? "Onbekend bestand";
                    string url = attachment.Url ?? "Geen URL";

                    Console.WriteLine($"    [BIJLAGE] {fileName}");
                    Console.WriteLine($"    [CDN] {url}");
                }
            }
        }

        Console.WriteLine();
        Console.WriteLine("=== Parser succesvol afgerond ===");
        Console.WriteLine();
        Console.WriteLine("=== PDF Generator Test Start ===");
        PdfGenerator.GeneratePDF(export);
    }
}
