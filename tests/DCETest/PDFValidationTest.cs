using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;

[TestClass]
public class PDFValidationTest
{
    [TestMethod]
    public void PdfGenerator_ShouldRunWithoutExceptions()
    {
        // Arrange
        QuestPDF.Settings.License = QuestPDF.Infrastructure.LicenseType.Community;

        var export = new DiscordExport();

        export.Messages.Add(new DiscordMessage
        {
            Timestamp = DateTime.Now,
            Content = "PDF validatie test",
            Author = new DiscordAuthor
            {
                Name = "TestUser"
            }
        });

        // Act
        Exception? exception = null;

        try
        {
            PdfGenerator.GeneratePDF(export);
        }
        catch (Exception ex)
        {
            exception = ex;
        }

        // Assert
        Assert.IsNull(exception, $"PDF generatie faalde: {exception?.Message}");
    }
}