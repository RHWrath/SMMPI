using System;
using System.IO;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Layers.Persistence.Models; // Hierbij wordt de verwijzing naar de Models alvast gemaakt.

namespace Layers.Persistence
{
    internal static class JSONParser
    {
        // Functie die de input JSON file parsed en wacht totdat dit klaar is met parsen.
        // Daarna kan deze data worden doorgestuurd naar de Normalisator.

        private static async Task Main(string[] args)
        {
            await ParseJSON();
        }

        private static async Task ParseJSON()
        {
            Console.WriteLine("Grabbing input JSON from Evidence Repository...");

            string inputFilePath = "FOLDER/INPUT.JSON";

            if (!File.Exists(inputFilePath))
            {
                Console.WriteLine("Input JSON file doesn't exist.");
                return;
            }

            // Read JSON file from the input folder and store it in a string variable.
            string RAW_JSON = await File.ReadAllTextAsync(inputFilePath);

            if (string.IsNullOrWhiteSpace(RAW_JSON))
            {
                Console.WriteLine("Input JSON file is empty.");
                return;
            }

            DiscordExport? export = JsonConvert.DeserializeObject<DiscordExport>(RAW_JSON);

            if (export == null)
            {
                Console.WriteLine("Export is empty or couldn't be parsed.");
                return;
            }

            if (export.Messages == null || export.Messages.Count == 0)
            {
                Console.WriteLine("Export contains no messages.");
                return;
            }

            Console.WriteLine("JSON Parsing Complete.");
            Console.WriteLine("Sending parsed JSON to Normalisator...");

            // Deel 1: het inlezen van de JSON file, het parsen van de inhoud
            // en een nacontrole uitvoeren of dit juist gedaan is.

            //________________________________________________________________

            // Normalisator.
            // Hier wordt de geparste data voorlopig gecontroleerd via Console output.
            // Later kan hier de echte Normalisator worden aangeroepen.

            foreach (var message in export.Messages)
            {
                string timestamp = message.Timestamp?.ToString() ?? "No timestamp";
                string author = message.Author?.Nickname ?? "Unknown author";
                string content = message.Content ?? "No content";

                Console.WriteLine($"[{timestamp}] {author}: {content}");
            }

            Console.WriteLine("Done.");

            // Deel 2: het doorsturen van de geparste JSON naar de Normalisator.cs.

            //________________________________________________________________
        }
    }
}
