using System;
using Newtonsoft.Json;
using QuestPDF;
using Layers.Persistence

//Logisch dat nu nog de "Output folder", "Input folder" en de files die genaamd worden placeholder names hebben.
//deze worden op termijn aangepast.

namespace Layers.Persistence
{
    //Functie die PDF genereert en wacht totdat dit klaar is met genereren.
    private static async Task PDFGenerator()
    {
        await GeneratePDF();
    }
    //Read files out of Clean Input folder.
    Console.Writeline("Starting PDF Generation");
    private readonly string inputFolder = "FOLDER";

    //Methode aanmaken die daadwerkelijk de PDF genereert en deze opslaat in de output folder.
    private static void GeneratePDF()
        {
        //Read all files from the input folder and store them in a list.
        List[] files = Directory.GetFiles(inputFolder);

        //________________________________________________________________

        //Use Library QuestPDF to generate PDF from the Files
        foreach (string file in files)
            {
            //Generate PDF from the LIST that has been made from the files in the input folder.
            //QUESTPDF logica word hier geplaatst.
            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(2, Unit.Centimetre);

                    page.Content().Column(column =>
                    {
                        column.Item().Text("PDF Generation");
                        column.Item().Text($"Generated from file: {file}");
                    });
                });
            //Send Generated PDF to output folder.
            }).GeneratePdf(outputPath);

            //________________________________________________________________

            //if outputfolder contains the generated PDF, then print "PDF Generation Completed" in the console.
            if (File.Exists(OutputFolder + "GeneratedPDF.pdf"))
            {
                Console.Writeline("PDF Generation Completed");
            }
            //als dit niet het geval is, dan krijg je een foutmelding.
            else
            {
                //if outputfolder does not contain the generated PDF, then print "PDF Generation Failed" in the console.
                Console.Writeline("PDF Generation Failed, Try again.");
            }
        }


