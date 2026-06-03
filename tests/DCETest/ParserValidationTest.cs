using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;
using Newtonsoft.Json;

[TestClass]
public class ParserValidationTests
{
    [TestMethod]
    public void Parser_ValidJson_ReturnsDiscordExportWithMessages()
    {
        string rawJson = """
        {
          "messages": [
            {
              "id": "1",
              "timestamp": "2026-04-23T19:58:06",
              "content": "Testbericht",
              "author": {
                "name": "TestUser"
              }
            }
          ],
          "messageCount": 1
        }
        """;

        DiscordExport? export = JsonParserService.DeserializeDiscordExport(rawJson);

        Assert.IsNotNull(export);
        Assert.IsTrue(JsonParserService.HasMessages(export));
    }

    [TestMethod]
    public void Parser_InvalidJson_ThrowsJsonReaderException()
    {
        string rawJson = "{ invalid json ";

        try
        {
            JsonParserService.DeserializeDiscordExport(rawJson);
            Assert.Fail("Expected JsonReaderException was not thrown.");
        }
        catch (Newtonsoft.Json.JsonReaderException)
        {
            Assert.IsTrue(true);
        }
    }

    [TestMethod]
    public void Parser_EmptyExport_ReturnsNoMessages()
    {
        var export = new DiscordExport();

        bool result = JsonParserService.HasMessages(export);

        Assert.IsFalse(result);
    }

    [TestMethod]
    public void Parser_MessageWithoutContent_ReturnsGeenTekst()
    {
        var message = new DiscordMessage
        {
            Content = ""
        };

        string result = JsonParserService.GetContent(message);

        Assert.AreEqual("[Geen tekst]", result);
    }

    [TestMethod]
    public void Parser_MessageWithAttachment_ContainsCdnUrl()
    {
        var message = new DiscordMessage();

        message.Attachments.Add(new DiscordAttachment
        {
            FileName = "test.jpg",
            Url = "https://cdn.discordapp.com/attachments/test.jpg"
        });

        Assert.AreEqual(1, message.Attachments.Count);
        Assert.AreEqual("test.jpg", message.Attachments[0].FileName);
        Assert.IsTrue(message.Attachments[0].Url!.Contains("cdn.discordapp.com"));
    }
}