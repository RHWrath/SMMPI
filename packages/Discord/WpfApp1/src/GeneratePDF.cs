using System;
using System.IO;
using System.Windows;
using QuestPDF.Fluent;
using QuestPDF.Infrastructure;
using SMMPI.Infrastructure.Plugins.Tools;

public static class PdfGenerator
{
    public static void GeneratePDF(DiscordExport export)
    {
        string outputFolder = Path.Combine(SolutionRoot.Get(), "Output", "GeneratedPDF");

        SolutionRoot.checkDirectoryExistsAndCreate(outputFolder);

        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");

        string outputPath = Path.Combine(
            outputFolder,
            $"DiscordExport_{timestamp}.pdf");

        Console.WriteLine($"PDF output path: {outputPath}");

        Document.Create(container =>
        {
            container.Page(page =>
            {
                page.Margin(30);

                page.Header()
                    .Text("Discord Export Rapport")
                    .FontSize(20)
                    .Bold();

                page.Content()
                    .Column(column =>
                    {
                        foreach (var message in export.Messages)
                        {
                            string author = message.Author?.Nickname
                                            ?? message.Author?.Name
                                            ?? "Onbekende auteur";

                            string content = string.IsNullOrWhiteSpace(message.Content)
                                ? "[Geen tekst]"
                                : message.Content;

                            column.Item().Text($"[{message.Timestamp:yyyy-MM-dd HH:mm:ss}] {author}")
                                .Bold();

                            column.Item().Text(content);

                            if (message.Attachments != null && message.Attachments.Count > 0)
                            {
                                foreach (var attachment in message.Attachments)
                                {
                                    string fileName = attachment.FileName ?? "Onbekend bestand";
                                    string url = attachment.Url ?? "Geen URL";

                                    column.Item().Text($"Bijlage: {fileName}");
                                    column.Item().Text($"CDN: {url}");
                                }
                            }

                            column.Item().PaddingBottom(10);
                        }
                    });

                page.Footer()
                    .AlignCenter()
                    .Text(x =>
                    {
                        x.Span("Pagina ");
                        x.CurrentPageNumber();
                    });
            });
        })
        .GeneratePdf(outputPath);

        Console.WriteLine();
        Console.WriteLine($"[PASS] PDF gegenereerd: {outputPath}");

        MessageBox.Show($"PDF succesvol gegenereerd:\n{outputPath}", "PDF Generator", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}