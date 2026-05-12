using System;
using System.Collections.Generic;
using System.IO;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace Layers.Persistence
{
    internal static class PDFGenerator
    {
        public static void GeneratePDF(List<ReportMessage> messages, string outputFilePath)
        {
            if (messages == null || messages.Count == 0)
            {
                Console.WriteLine("No messages available for PDF generation.");
                return;
            }

            string? outputDirectory = Path.GetDirectoryName(outputFilePath);

            if (!string.IsNullOrWhiteSpace(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            QuestPDF.Settings.License = LicenseType.Community;

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(2, Unit.Centimetre);
                    page.PageColor(Colors.White);

                    page.DefaultTextStyle(text =>
                        text.FontSize(10));

                    page.Header()
                        .Column(column =>
                        {
                            column.Item()
                                .Text("Discord Chat Rapportage")
                                .SemiBold()
                                .FontSize(20);

                            column.Item()
                                .Text($"Gegenereerd op: {DateTime.Now:dd-MM-yyyy HH:mm}")
                                .FontSize(9);
                        });

                    page.Content()
                        .PaddingVertical(10)
                        .Column(column =>
                        {
                            column.Spacing(8);

                            foreach (ReportMessage message in messages)
                            {
                                column.Item()
                                    .Border(1)
                                    .Padding(8)
                                    .Column(messageColumn =>
                                    {
                                        messageColumn.Spacing(4);

                                        messageColumn.Item()
                                            .Text($"{message.AuthorName} - {message.Timestamp:dd-MM-yyyy HH:mm:ss}")
                                            .SemiBold()
                                            .FontSize(11);

                                        messageColumn.Item()
                                            .Text(message.Content)
                                            .FontSize(10);

                                        if (message.Attachments.Count > 0)
                                        {
                                            messageColumn.Item()
                                                .Text("Bijlagen:")
                                                .SemiBold()
                                                .FontSize(9);

                                            foreach (ReportAttachment attachment in message.Attachments)
                                            {
                                                messageColumn.Item()
                                                    .Text($"- {attachment.FileName} ({attachment.FileSizeBytes} bytes)")
                                                    .FontSize(9);

                                                if (!string.IsNullOrWhiteSpace(attachment.Url))
                                                {
                                                    messageColumn.Item()
                                                        .Text(attachment.Url)
                                                        .FontSize(8);
                                                }
                                            }
                                        }
                                    });
                            }
                        });

                    page.Footer()
                        .AlignCenter()
                        .Text(text =>
                        {
                            text.Span("Pagina ");
                            text.CurrentPageNumber();
                            text.Span(" van ");
                            text.TotalPages();
                        });
                });
            })
            .GeneratePdf(outputFilePath);

            Console.WriteLine($"PDF generated successfully: {outputFilePath}");
        }
    }
}
