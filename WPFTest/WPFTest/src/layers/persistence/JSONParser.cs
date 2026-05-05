using System;
using System.IO;
using System.Collections.Generic;
using Newtonsoft.Json;
using Layers.Persistence.Models; //hierbij wordt de verwijzing naar de Normalisator alvast gemaakt, dit zorgt dat deze code al klaar is om de data die uit de JSON file wordt gehaald door te sturen naar de Normalisator.

//Logisch dat nu nog de "Output folder", "Input folder" en de files die genaamd worden placeholder names hebben.
//deze worden op termijn aangepast.

namespace Layers.Persistence
{
    internal static class JSONParser
    {
        //Functie die de Input JSON file parsed en wacht totdat dit klaar is met parsen, daarna stuurt ie deze door naar de PDF Generator.

        private static async Task Main(string[] args) //Hierbij maken we een task die wacht totdat het parsen van de JSON klaar is, voordat deze verder gaat met de volgende stappen.
        {
            await ParseJSON();
        }
        private static async Task ParseJSON() //De task heeft de volgende structuur.
        {
            // Implement JSON parsing logic here
                Console.WriteLine("Grabbing input JSON from Evidence Repository...");
                //Read JSON file from the input folder and store it in a variable.
                    string RAW_JSON = File.ReadAllText("FOLDER/INPUT.JSON"); //Hierbij wordt de JSON file gelezen en opgeslagen als een Variabele, deze variabele is een string array omdat er meerdere JSON files kunnen zijn in de input folder.

            DiscordExport? export = JsonConvert.DeserializeObject<DiscordExport>(RAW_JSON); //Hierbij wordt de JSON file geparst en opgeslagen als een DiscordExport object.

            if (export == null) //Als de export leeg is of niet bestaat, dan krijg je een foutmelding.
            {
                Console.WriteLine("Export is empty or doesn't exist.");
                return;
            }

            Console.WriteLine("JSON Parsing Complete.");
            Console.WriteLine("Sending parsed JSON to Normalisator...");

            //Deel 1 van de structuur, het inlezen van de JSON file, het parsen van de inhoud en een nacontrole invoeren of dit juist gedaan is.

            //________________________________________________________________

            //Normalisator.

            //Stuur deze variable door naar de Normalisator
            foreach (var message in export.Messages)
            {
                Console.WriteLine($"[{message.Timestamp}] {message.Author?.Nickname}: {message.Content}");
            }

            Console.WriteLine("Done.");

            //Deel 2 van de structuur, het doorsturen van de geparste JSON naar de Normalisator.css. 

            //________________________________________________________________
        }
    }
}