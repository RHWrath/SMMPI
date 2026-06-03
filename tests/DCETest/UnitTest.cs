using Microsoft.VisualStudio.TestTools.UnitTesting;
using Newtonsoft.Json;

[TestClass]
public class ParserUnitTests
{
    [TestMethod]
    public void GetContent_WithEmptyContent_ReturnsGeenTekst()
    {
        // Arrange
        var message = new DiscordMessage
        {
            Content = ""
        };

        // Act
        string result = JsonParserService.GetContent(message);

        // Assert
        Assert.AreEqual("[Geen tekst]", result);
    }

    [TestMethod]
    public void GetAuthorName_WithNickname_ReturnsNickname()
    {
        // Arrange
        var message = new DiscordMessage
        {
            Author = new DiscordAuthor
            {
                Nickname = "Jens"
            }
        };

        // Act
        string result = JsonParserService.GetAuthorName(message);

        // Assert
        Assert.AreEqual("Jens", result);
    }

    [TestMethod]
    public void HasMessages_WithMessages_ReturnsTrue()
    {
        // Arrange
        var export = new DiscordExport();

        export.Messages.Add(new DiscordMessage());

        // Act
        bool result = JsonParserService.HasMessages(export);

        // Assert
        Assert.IsTrue(result);
    }
}