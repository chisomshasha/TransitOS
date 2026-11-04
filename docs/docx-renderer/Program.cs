// TransitOS testing manual — DOCX renderer.
//
// Backend S (direct OpenXML SDK): the builtin CLI create surface has no
// table support, and a testing manual is almost entirely tables.
//
// Style family: ModernCorporate (see AestheticRecipeSamples.cs) —
// 1.25x modular scale, dark navy headings, soft-black body, banded
// table rows, horizontal-only table borders.

using System.Text.Json;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using A = DocumentFormat.OpenXml.Drawing;
using DW = DocumentFormat.OpenXml.Drawing.Wordprocessing;
using PIC = DocumentFormat.OpenXml.Drawing.Pictures;

namespace DocxRenderer;

internal static class Program
{
    // ── palette (ModernCorporate) ──────────────────────────────────────
    const string Navy = "1F3864";
    const string NavyMid = "2E5496";
    const string Body = "333333";
    const string Muted = "5A6472";
    const string Rule = "BFBFBF";
    const string RowRule = "D9D9D9";
    const string Band = "F4F6FA";
    const string HeadFill = "1F3864";
    const string CalloutFill = "EEF3FB";

    static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("usage: DocxRenderer <plan.json> <out.docx>");
            return 2;
        }

        var plan = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        using (var doc = WordprocessingDocument.Create(args[1], WordprocessingDocumentType.Document))
        {
            var main = doc.AddMainDocumentPart();
            main.Document = new Document(new Body());
            var body = main.Document.Body!;

            AddStyles(main);
            AddNumbering(main);
            var (headerPart, footerPart) = AddHeaderFooter(main, plan.GetProperty("title").GetString() ?? "TransitOS");

            var section = new SectionProperties(
                new PageSize { Width = 11906U, Height = 16838U },   // A4
                new PageMargin
                {
                    Top = 900, Bottom = 900, Left = 850, Right = 850,
                    Header = 480, Footer = 480, Gutter = 0
                },
                new Columns { Space = "708" },
                new DocGrid { LinePitch = 360 }
            );

            BuildCover(body, plan, main);
            BuildToc(body);
            BuildBlocks(body, plan, main);

            body.Append(section);

            // The header and footer references must be attached to the
            // section once it is in the body. Doing it earlier leaves
            // both parts orphaned and they never render.
            section.Append(new HeaderReference
            {
                Type = HeaderFooterValues.Default,
                Id = main.GetIdOfPart(headerPart)
            });
            section.Append(new FooterReference
            {
                Type = HeaderFooterValues.Default,
                Id = main.GetIdOfPart(footerPart)
            });

            main.Document.Save();
        }

        Console.WriteLine($"wrote {args[1]}");
        return 0;
    }

    // ── styles ──────────────────────────────────────────────────────────
    static void AddStyles(MainDocumentPart main)
    {
        var part = main.AddNewPart<StyleDefinitionsPart>();
        part.Styles = new Styles();
        var styles = part.Styles;

        styles.Append(new DocDefaults(
            new RunPropertiesDefault(
                new RunPropertiesBaseStyle(
                    new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos", ComplexScript = "Calibri" },
                    new FontSize { Val = "21" },              // 10.5pt body
                    new FontSizeComplexScript { Val = "21" },
                    new Color { Val = Body },
                    new Languages { Val = "en-US" })),
            new ParagraphPropertiesDefault(
                new ParagraphPropertiesBaseStyle(
                    new SpacingBetweenLines
                    {
                        Line = "264",                        // 1.10x
                        LineRule = LineSpacingRuleValues.Auto,
                        After = "140"
                    }))));

        styles.Append(Para("Normal", "Normal", true, 0,
            new StyleParagraphProperties(
                new SpacingBetweenLines { After = "140", Line = "264", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new FontSize { Val = "21" },
                new Color { Val = Body })));

        // Headings — 1.25x modular scale from a 10.5pt body.
        styles.Append(Heading("Heading1", "heading 1", 1, 40, Navy, "Aptos Display", 320, 140));
        styles.Append(Heading("Heading2", "heading 2", 2, 32, Navy, "Aptos Display", 260, 110));
        styles.Append(Heading("Heading3", "heading 3", 3, 26, NavyMid, "Aptos Display", 220, 90));
        styles.Append(Heading("Heading4", "heading 4", 4, 22, NavyMid, "Aptos", 180, 70));

        // Cover
        styles.Append(Para("CoverTitle", "Cover Title", false, 1,
            new StyleParagraphProperties(
                new SpacingBetweenLines { Before = "0", After = "160", Line = "240", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos Display", HighAnsi = "Aptos Display" },
                new FontSize { Val = "64" },
                new Color { Val = Navy })));
        styles.Append(Para("CoverSub", "Cover Subtitle", false, 2,
            new StyleParagraphProperties(
                new SpacingBetweenLines { Before = "0", After = "360", Line = "264", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new FontSize { Val = "28" },
                new Color { Val = Muted })));

        // Callout
        styles.Append(Para("Callout", "Callout", false, 3,
            new StyleParagraphProperties(
                new ParagraphBorders(
                    new LeftBorder { Val = BorderValues.Single, Size = 18, Space = 8, Color = NavyMid }),
                new Shading { Val = ShadingPatternValues.Clear, Color = "auto", Fill = CalloutFill },
                new SpacingBetweenLines { Before = "120", After = "160", Line = "264", LineRule = LineSpacingRuleValues.Auto },
                new Indentation { Left = "200", Right = "160" }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new FontSize { Val = "21" },
                new Color { Val = Body })));

        // Small meta text
        styles.Append(Para("Meta", "Meta", false, 4,
            new StyleParagraphProperties(
                new SpacingBetweenLines { Before = "0", After = "60" }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new FontSize { Val = "19" },
                new Color { Val = Muted })));

        // Caption
        styles.Append(Para("Caption", "Caption", false, 8,
            new StyleParagraphProperties(
                new Justification { Val = JustificationValues.Center },
                new SpacingBetweenLines { Before = "0", After = "180" }),
            new StyleRunProperties(
                new Italic(),
                new FontSize { Val = "17" },
                new Color { Val = "64748B" })));

        // Code
        styles.Append(Para("CodeBlock", "Code Block", false, 7,
            new StyleParagraphProperties(
                new Shading { Val = ShadingPatternValues.Clear, Color = "auto", Fill = "F4F6FA" },
                new ParagraphBorders(
                    new LeftBorder { Val = BorderValues.Single, Size = 12, Space = 6, Color = "C7D0DE" }),
                new SpacingBetweenLines { Before = "0", After = "0", Line = "240", LineRule = LineSpacingRuleValues.Auto },
                new Indentation { Left = "180" }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Consolas", HighAnsi = "Consolas", ComplexScript = "Consolas" },
                new FontSize { Val = "17" },
                new Color { Val = "1F2937" })));

        // Table text
        styles.Append(Para("TableText", "Table Text", false, 5,
            new StyleParagraphProperties(
                new SpacingBetweenLines { Before = "20", After = "20", Line = "240", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new FontSize { Val = "17" },                  // 8.5pt
                new Color { Val = Body })));
        styles.Append(Para("TableHead", "Table Head", false, 6,
            new StyleParagraphProperties(
                new SpacingBetweenLines { Before = "30", After = "30", Line = "240", LineRule = LineSpacingRuleValues.Auto }),
            new StyleRunProperties(
                new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                new Bold(),
                new FontSize { Val = "17" },
                new Color { Val = "FFFFFF" })));

        part.Styles.Save();
    }

    static Style Para(string id, string name, bool isDefault, int priority,
        StyleParagraphProperties pPr, StyleRunProperties rPr)
    {
        var s = new Style(
            new StyleName { Val = name },
            new BasedOn { Val = "Normal" },
            new UIPriority { Val = priority },
            new PrimaryStyle(),
            pPr, rPr)
        { Type = StyleValues.Paragraph, StyleId = id };
        if (isDefault) s.Default = true;
        return s;
    }

    static Style Heading(string id, string name, int level, int halfPts, string color,
        string font, int before, int after)
    {
        return new Style(
            new StyleName { Val = name },
            new BasedOn { Val = "Normal" },
            new NextParagraphStyle { Val = "Normal" },
            new UIPriority { Val = 9 },
            new PrimaryStyle(),
            new StyleParagraphProperties(
                new KeepNext(),
                new KeepLines(),
                new SpacingBetweenLines
                {
                    Before = before.ToString(),
                    After = after.ToString(),
                    Line = "240",
                    LineRule = LineSpacingRuleValues.Auto
                },
                new OutlineLevel { Val = level - 1 }),
            new StyleRunProperties(
                new RunFonts { Ascii = font, HighAnsi = font },
                new FontSize { Val = halfPts.ToString() },
                new Color { Val = color }))
        { Type = StyleValues.Paragraph, StyleId = id };
    }

    // ── numbering (bullets) ─────────────────────────────────────────────
    static void AddNumbering(MainDocumentPart main)
    {
        var part = main.AddNewPart<NumberingDefinitionsPart>();
        var numbering = new Numbering();
        var abs = new AbstractNum(
            new Level(
                new NumberingFormat { Val = NumberFormatValues.Bullet },
                new LevelText { Val = "•" },
                new LevelJustification { Val = LevelJustificationValues.Left },
                new PreviousParagraphProperties(new Indentation { Left = "360", Hanging = "220" }),
                new NumberingSymbolRunProperties(
                    new RunFonts { Ascii = "Symbol", HighAnsi = "Symbol", Hint = FontTypeHintValues.Default }))
            { LevelIndex = 0 })
        { AbstractNumberId = 1 };
        numbering.Append(abs);
        numbering.Append(new NumberingInstance(
            new AbstractNumId { Val = 1 })
        { NumberID = 1 });
        part.Numbering = numbering;
        part.Numbering.Save();
    }

    // ── header / footer ─────────────────────────────────────────────────
    static (HeaderPart header, FooterPart footer) AddHeaderFooter(MainDocumentPart main, string title)
    {
        var hp = main.AddNewPart<HeaderPart>();
        hp.Header = new Header(
            new Paragraph(
                new ParagraphProperties(
                    new ParagraphBorders(
                        new BottomBorder { Val = BorderValues.Single, Size = 4, Space = 4, Color = Rule }),
                    new SpacingBetweenLines { After = "60" },
                    new Justification { Val = JustificationValues.Right }),
                new Run(
                    new RunProperties(
                        new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                        new FontSize { Val = "16" },
                        new Color { Val = Muted }),
                    new Text(title))));
        hp.Header.Save();

        var fp = main.AddNewPart<FooterPart>();
        var footer = new Footer(
            new Paragraph(
                new ParagraphProperties(
                    new ParagraphBorders(
                        new TopBorder { Val = BorderValues.Single, Size = 4, Space = 4, Color = Rule }),
                    new SpacingBetweenLines { Before = "60" },
                    new Justification { Val = JustificationValues.Center }),
                new Run(
                    new RunProperties(
                        new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                        new FontSize { Val = "16" },
                        new Color { Val = Muted }),
                    new Text("Page ") { Space = SpaceProcessingModeValues.Preserve }),
                new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
                new Run(new FieldCode(" PAGE ") { Space = SpaceProcessingModeValues.Preserve }),
                new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }),
                new Run(new Text("1")),
                new Run(new FieldChar { FieldCharType = FieldCharValues.End }),
                new Run(new Text(" of ") { Space = SpaceProcessingModeValues.Preserve }),
                new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
                new Run(new FieldCode(" NUMPAGES ") { Space = SpaceProcessingModeValues.Preserve }),
                new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }),
                new Run(new Text("1")),
                new Run(new FieldChar { FieldCharType = FieldCharValues.End })));
        fp.Footer = footer;
        fp.Footer.Save();

        return (hp, fp);
    }

    // ── cover + TOC ─────────────────────────────────────────────────────
    static void BuildCover(Body body, JsonElement plan, MainDocumentPart main)
    {
        // The app's real logo — the same asset the app ships as its icon.
        if (plan.TryGetProperty("cover", out var coverObj)
            && coverObj.TryGetProperty("logo", out var logoEl)
            && logoEl.GetString() is string logoPath
            && File.Exists(logoPath))
        {
            var logoPart = main.AddImagePart(ImagePartType.Png);
            using (var fs = File.OpenRead(logoPath))
            {
                logoPart.FeedData(fs);
            }
            var logoRel = main.GetIdOfPart(logoPart);
            var (lcx, lcy) = PngSize(logoPath, 1828800L, 1828800L);   // 2 inches

            var logoPic = new PIC.Picture(
                new PIC.NonVisualPictureProperties(
                    new PIC.NonVisualDrawingProperties { Id = 0U, Name = "TransitOS logo" },
                    new PIC.NonVisualPictureDrawingProperties()),
                new A.BlipFill(
                    new A.Blip { Embed = logoRel },
                    new A.Stretch(new A.FillRectangle())),
                new PIC.ShapeProperties(
                    new A.Transform2D(
                        new A.Offset { X = 0L, Y = 0L },
                        new A.Extents { Cx = lcx, Cy = lcy }),
                    new A.PresetGeometry(new A.AdjustValueList())
                    { Preset = A.ShapeTypeValues.Rectangle }));

            var logoDrawing = new Drawing(
                new DW.Inline(
                    new DW.Extent { Cx = lcx, Cy = lcy },
                    new DW.EffectExtent
                    {
                        LeftEdge = 0L, TopEdge = 0L,
                        RightEdge = 0L, BottomEdge = 0L
                    },
                    new DW.DocProperties { Id = 2U, Name = "TransitOS logo" },
                    new DW.NonVisualGraphicFrameDrawingProperties(
                        new A.GraphicFrameLocks { NoChangeAspect = true }),
                    new A.Graphic(
                        new A.GraphicData(logoPic)
                        {
                            Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture"
                        }))
                {
                    DistanceFromTop = 0U,
                    DistanceFromBottom = 0U,
                    DistanceFromLeft = 0U,
                    DistanceFromRight = 0U
                });

            body.Append(new Paragraph(
                new ParagraphProperties(
                    new Justification { Val = JustificationValues.Center },
                    new SpacingBetweenLines { Before = "900", After = "240" }),
                new Run(logoDrawing)));
        }

        body.Append(new Paragraph(
            new ParagraphProperties(
                new ParagraphStyleId { Val = "CoverTitle" },
                new Justification { Val = JustificationValues.Center }),
            new Run(new Text(plan.GetProperty("title").GetString() ?? "TransitOS"))));

        var cover = plan.TryGetProperty("cover", out var cv) ? cv : default;

        if (cover.ValueKind == JsonValueKind.Object
            && cover.TryGetProperty("subtitle", out var subEl)
            && subEl.GetString() is string subText
            && !string.IsNullOrWhiteSpace(subText))
        {
            body.Append(new Paragraph(
                new ParagraphProperties(
                    new ParagraphStyleId { Val = "CoverSub" },
                    new Justification { Val = JustificationValues.Center }),
                new Run(new Text(subText))));
        }

        var meta = new List<string>();
        if (cover.ValueKind == JsonValueKind.Object
            && cover.TryGetProperty("meta", out var metaEl)
            && metaEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var m in metaEl.EnumerateArray())
            {
                var t = m.GetString();
                if (!string.IsNullOrWhiteSpace(t)) meta.Add(t);
            }
        }

        foreach (var line in meta)
        {
            body.Append(new Paragraph(
                new ParagraphProperties(
                    new ParagraphBorders(
                        new TopBorder { Val = BorderValues.Single, Size = 12, Space = 1, Color = Navy }),
                    new SpacingBetweenLines { Before = "200", After = "120" }),
                new Run(
                    new RunProperties(
                        new RunFonts { Ascii = "Aptos", HighAnsi = "Aptos" },
                        new Bold(),
                        new FontSize { Val = "20" },
                        new Color { Val = Navy }),
                    new Text(line))));
        }

        if (cover.ValueKind == JsonValueKind.Object
            && cover.TryGetProperty("note", out var noteEl)
            && noteEl.GetString() is string noteText
            && !string.IsNullOrWhiteSpace(noteText))
        {
            body.Append(new Paragraph(
                new ParagraphProperties(new ParagraphStyleId { Val = "Meta" }),
                new Run(new Text(noteText))));
        }

        body.Append(new Paragraph(new Run(new Break { Type = BreakValues.Page })));
    }

    static void BuildToc(Body body)
    {
        body.Append(new Paragraph(
            new ParagraphProperties(new ParagraphStyleId { Val = "Heading1" }),
            new Run(new Text("Contents"))));

        body.Append(new Paragraph(
            new ParagraphProperties(new SpacingBetweenLines { After = "200" }),
            new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }),
            new Run(new FieldCode(" TOC \\o \"1-3\" \\h \\z \\u ")
            { Space = SpaceProcessingModeValues.Preserve }),
            new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }),
            new Run(
                new RunProperties(new Color { Val = Muted }),
                new Text("Right-click and choose “Update Field” to build the table of contents.")),
            new Run(new FieldChar { FieldCharType = FieldCharValues.End })));

        body.Append(new Paragraph(new Run(new Break { Type = BreakValues.Page })));
    }


    // A4 (11906 twips) minus the 850-twip left/right margins.
    const long MaxContentWidthEmu = 11906L * 635L - 850L * 635L - 850L * 635L;

    // A phone screenshot beside its caption: about 2.5 inches wide and
    // never taller than the text area.
    const long FigureWidthEmu = 2286000L;          // 2.5in
    const long FigureMaxHeightEmu = 5943600L;      // 6.5in

    /// <summary>Read a PNG's pixel size from its IHDR chunk and scale it to fit.</summary>
    static (long cx, long cy) PngSize(string path, long maxWidthEmu, long maxHeightEmu)
    {
        try
        {
            using var fs = File.OpenRead(path);
            var header = new byte[24];
            if (fs.Read(header, 0, 24) < 24) return (maxWidthEmu, maxWidthEmu);
            // Bytes 0-7 signature, 8-11 length, 12-15 "IHDR", 16-19 width, 20-23 height.
            long w = ((long)header[16] << 24) | ((long)header[17] << 16)
                    | ((long)header[18] << 8) | header[19];
            long h = ((long)header[20] << 24) | ((long)header[21] << 16)
                    | ((long)header[22] << 8) | header[23];
            if (w <= 0 || h <= 0) return (maxWidthEmu, maxWidthEmu);

            const long EmuPerPixel = 9525L;   // 96 dpi
            long cx = w * EmuPerPixel;
            long cy = h * EmuPerPixel;
            if (cx > maxWidthEmu)
            {
                cy = (long)(cy * ((double)maxWidthEmu / cx));
                cx = maxWidthEmu;
            }
            if (cy > maxHeightEmu)
            {
                cx = (long)(cx * ((double)maxHeightEmu / cy));
                cy = maxHeightEmu;
            }
            return (cx, cy);
        }
        catch
        {
            return (maxWidthEmu, maxWidthEmu);
        }
    }

    // ── blocks ──────────────────────────────────────────────────────────
    static void BuildBlocks(Body body, JsonElement plan, MainDocumentPart main)
    {
        foreach (var b in plan.GetProperty("blocks").EnumerateArray())
        {
            switch (b.GetProperty("type").GetString())
            {
                case "title":
                case "subtitle":
                    break;   // already on the cover
                case "heading":
                    {
                        var level = Math.Clamp(b.GetProperty("level").GetInt32(), 1, 4);
                        body.Append(new Paragraph(
                            new ParagraphProperties(new ParagraphStyleId { Val = "Heading" + level }),
                            new Run(new Text(b.GetProperty("text").GetString() ?? ""))));
                        break;
                    }
                case "paragraph":
                    body.Append(new Paragraph(
                        new ParagraphProperties(new ParagraphStyleId { Val = "Normal" }),
                        new Run(new Text(b.GetProperty("text").GetString() ?? ""))));
                    break;
                case "callout":
                    body.Append(new Paragraph(
                        new ParagraphProperties(new ParagraphStyleId { Val = "Callout" }),
                        new Run(new Text(b.GetProperty("text").GetString() ?? ""))));
                    break;
                case "bullets":
                    {
                        foreach (var item in b.GetProperty("items").EnumerateArray())
                        {
                            body.Append(new Paragraph(
                                new ParagraphProperties(
                                    new ParagraphStyleId { Val = "Normal" },
                                    new NumberingProperties(
                                        new NumberingLevelReference { Val = 0 },
                                        new NumberingId { Val = 1 }),
                                    new SpacingBetweenLines { After = "60" },
                                    new Indentation { Left = "360", Hanging = "220" }),
                                new Run(new Text(item.GetString() ?? ""))));
                        }
                        break;
                    }
                case "image":
                    {
                        var relPath = b.GetProperty("path").GetString() ?? "";
                        var caption = b.TryGetProperty("caption", out var capEl)
                            ? capEl.GetString() ?? "" : "";
                        if (!File.Exists(relPath))
                        {
                            body.Append(new Paragraph(
                                new ParagraphProperties(new ParagraphStyleId { Val = "Normal" }),
                                new Run(new Text($"[missing image: {relPath}]"))));
                            break;
                        }

                        var imagePart = main.AddImagePart(ImagePartType.Png);
                        using (var fs = File.OpenRead(relPath))
                        {
                            imagePart.FeedData(fs);
                        }
                        var relId = main.GetIdOfPart(imagePart);
                        var (cx, cy) = PngSize(relPath, FigureWidthEmu, FigureMaxHeightEmu);

                        var pic = new PIC.Picture(
                            new PIC.NonVisualPictureProperties(
                                new PIC.NonVisualDrawingProperties
                                { Id = 0U, Name = Path.GetFileName(relPath) },
                                new PIC.NonVisualPictureDrawingProperties()),
                            new A.BlipFill(
                                new A.Blip { Embed = relId },
                                new A.Stretch(new A.FillRectangle())),
                            new PIC.ShapeProperties(
                                new A.Transform2D(
                                    new A.Offset { X = 0L, Y = 0L },
                                    new A.Extents { Cx = cx, Cy = cy }),
                                new A.PresetGeometry(new A.AdjustValueList())
                                { Preset = A.ShapeTypeValues.Rectangle },
                                new A.Outline(
                                    new A.SolidFill(
                                        new A.RgbColorModelHex { Val = "D8DEE9" }))
                                { Width = 9525 }));

                        var drawing = new Drawing(
                            new DW.Inline(
                                new DW.Extent { Cx = cx, Cy = cy },
                                new DW.EffectExtent
                                {
                                    LeftEdge = 0L, TopEdge = 0L,
                                    RightEdge = 0L, BottomEdge = 0L
                                },
                                new DW.DocProperties { Id = 1U, Name = "Picture" },
                                new DW.NonVisualGraphicFrameDrawingProperties(
                                    new A.GraphicFrameLocks { NoChangeAspect = true }),
                                new A.Graphic(
                                    new A.GraphicData(pic)
                                    {
                                        Uri = "http://schemas.openxmlformats.org/drawingml/2006/picture"
                                    }))
                            {
                                DistanceFromTop = 0U,
                                DistanceFromBottom = 0U,
                                DistanceFromLeft = 0U,
                                DistanceFromRight = 0U
                            });

                        // Caption cell
                        var captionPara = new Paragraph(
                            new ParagraphProperties(
                                new ParagraphStyleId { Val = "Caption" },
                                new Justification { Val = JustificationValues.Left }),
                            new Run(new Text(caption)));

                        // A borderless two-column table keeps the capture and
                        // its caption on the same line, so a phone-shaped
                        // screenshot does not eat a whole page.
                        var leftCell = new TableCell(
                            new TableCellProperties(
                                new TableCellWidth
                                { Width = FigureWidthEmu.ToString(), Type = TableWidthUnitValues.Dxa },
                                new TableCellVerticalAlignment
                                { Val = TableVerticalAlignmentValues.Center },
                                new TableCellMargin
                                {
                                    TopMargin = new TopMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    BottomMargin = new BottomMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    StartMargin = new StartMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    EndMargin = new EndMargin { Width = "160", Type = TableWidthUnitValues.Dxa }
                                }),
                            new Paragraph(
                                new ParagraphProperties(
                                    new Justification { Val = JustificationValues.Center },
                                    new SpacingBetweenLines { Before = "80", After = "80" }),
                                new Run(drawing)));

                        var rightCell = new TableCell(
                            new TableCellProperties(
                                new TableCellWidth
                                { Width = (MaxContentWidthEmu - FigureWidthEmu).ToString(), Type = TableWidthUnitValues.Dxa },
                                new TableCellVerticalAlignment
                                { Val = TableVerticalAlignmentValues.Top },
                                new TableCellMargin
                                {
                                    TopMargin = new TopMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    BottomMargin = new BottomMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    StartMargin = new StartMargin { Width = "0", Type = TableWidthUnitValues.Dxa },
                                    EndMargin = new EndMargin { Width = "0", Type = TableWidthUnitValues.Dxa }
                                }),
                            captionPara);

                        body.Append(new Table(
                            new TableProperties(
                                new TableWidth
                                { Width = MaxContentWidthEmu.ToString(), Type = TableWidthUnitValues.Dxa },
                                new TableLayout { Type = TableLayoutValues.Fixed },
                                new TableBorders(
                                    new TopBorder { Val = BorderValues.Nil },
                                    new BottomBorder { Val = BorderValues.Nil },
                                    new LeftBorder { Val = BorderValues.Nil },
                                    new RightBorder { Val = BorderValues.Nil },
                                    new InsideHorizontalBorder { Val = BorderValues.Nil },
                                    new InsideVerticalBorder { Val = BorderValues.Nil })),
                            new TableGrid(
                                new GridColumn { Width = FigureWidthEmu.ToString() },
                                new GridColumn { Width = (MaxContentWidthEmu - FigureWidthEmu).ToString() }),
                            new TableRow(leftCell, rightCell)));

                        body.Append(new Paragraph(
                            new ParagraphProperties(
                                new SpacingBetweenLines { Before = "0", After = "120" })));
                        break;
                    }
                case "code":
                    {
                        var code = b.GetProperty("text").GetString() ?? "";
                        var lines = code.Split('\n');
                        for (int i = 0; i < lines.Length; i++)
                        {
                            var pPr = new ParagraphProperties(
                                new ParagraphStyleId { Val = "CodeBlock" });
                            if (i == 0) pPr.SpacingBetweenLines = new SpacingBetweenLines { Before = "120", After = "0" };
                            if (i == lines.Length - 1) pPr.SpacingBetweenLines = new SpacingBetweenLines { Before = "0", After = "160" };
                            body.Append(new Paragraph(pPr,
                                new Run(new Text(lines[i]) { Space = SpaceProcessingModeValues.Preserve })));
                        }
                        break;
                    }
                case "table":
                    body.Append(BuildTable(b));
                    body.Append(new Paragraph(
                        new ParagraphProperties(new SpacingBetweenLines { After = "120", Line = "120", LineRule = LineSpacingRuleValues.Auto })));
                    break;
            }
        }
    }

    // ── table ───────────────────────────────────────────────────────────
    static Table BuildTable(JsonElement b)
    {
        var headers = b.GetProperty("headers").EnumerateArray().Select(h => h.GetString() ?? "").ToList();
        var rows = b.GetProperty("rows").EnumerateArray()
            .Select(r => r.EnumerateArray().Select(c => c.GetString() ?? "").ToList())
            .ToList();

        var n = headers.Count;
        var widths = ComputeWidths(headers, rows, n);

        var table = new Table();
        table.Append(new TableProperties(
            new TableWidth { Width = "5000", Type = TableWidthUnitValues.Pct },
            new TableLayout { Type = TableLayoutValues.Fixed },
            new TableBorders(
                new TopBorder { Val = BorderValues.Single, Size = 8, Space = 0, Color = Rule },
                new BottomBorder { Val = BorderValues.Single, Size = 8, Space = 0, Color = Rule },
                new LeftBorder { Val = BorderValues.None, Size = 0, Space = 0, Color = "auto" },
                new RightBorder { Val = BorderValues.None, Size = 0, Space = 0, Color = "auto" },
                new InsideHorizontalBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = RowRule },
                new InsideVerticalBorder { Val = BorderValues.None, Size = 0, Space = 0, Color = "auto" }),
            new TableCellMarginDefault(
                new TopMargin { Width = "40", Type = TableWidthUnitValues.Dxa },
                new StartMargin { Width = "72", Type = TableWidthUnitValues.Dxa },
                new BottomMargin { Width = "40", Type = TableWidthUnitValues.Dxa },
                new EndMargin { Width = "72", Type = TableWidthUnitValues.Dxa }),
            new TableLook { Val = "04A0" }));

        var grid = new TableGrid();
        foreach (var w in widths) grid.Append(new GridColumn { Width = w.ToString() });
        table.Append(grid);

        // Header row — repeats on every page, which matters for the long
        // endpoint tables that run over a page break.
        var head = new TableRow(new TableRowProperties(
            new TableHeader(),
            new CantSplit()));
        for (int c = 0; c < n; c++)
        {
            head.Append(new TableCell(
                new TableCellProperties(
                    new TableCellWidth { Width = widths[c].ToString(), Type = TableWidthUnitValues.Dxa },
                    new Shading { Val = ShadingPatternValues.Clear, Color = "auto", Fill = HeadFill },
                    new TableCellVerticalAlignment { Val = TableVerticalAlignmentValues.Center }),
                new Paragraph(
                    new ParagraphProperties(new ParagraphStyleId { Val = "TableHead" }),
                    new Run(new Text(headers[c])))));
        }
        table.Append(head);

        for (int r = 0; r < rows.Count; r++)
        {
            var row = new TableRow(new TableRowProperties(new CantSplit()));
            for (int c = 0; c < n; c++)
            {
                var text = c < rows[r].Count ? rows[r][c] : "";
                var tcPr = new TableCellProperties(
                    new TableCellWidth { Width = widths[c].ToString(), Type = TableWidthUnitValues.Dxa },
                    new TableCellVerticalAlignment { Val = TableVerticalAlignmentValues.Top });
                if (r % 2 == 1)
                {
                    tcPr.Append(new Shading
                    {
                        Val = ShadingPatternValues.Clear,
                        Color = "auto",
                        Fill = Band
                    });
                }

                var para = new Paragraph(
                    new ParagraphProperties(new ParagraphStyleId { Val = "TableText" }));

                // Centre the narrow columns (number, severity, result).
                bool centre = text is "☐" || RegexSeverity(text) || IsNumeric(text);
                if (centre)
                {
                    para.ParagraphProperties!.Append(new Justification { Val = JustificationValues.Center });
                }

                para.Append(new Run(new Text(text)));
                row.Append(new TableCell(tcPr, para));
            }
            table.Append(row);
        }

        return table;
    }

    static bool RegexSeverity(string s) =>
        s.Length is 2 or 3 && s.StartsWith("P") && s.Skip(1).All(char.IsDigit);

    static bool IsNumeric(string s) => s.Length > 0 && s.All(char.IsDigit);

    /// <summary>
    /// Column widths proportional to content, but never narrower than the
    /// longest unbreakable word in that column.
    ///
    /// Without the word-based minimum a header like "Method" collapses to
    /// "M / eth / od" and the cell contents break mid-word — which makes
    /// a 40-page checklist unreadable.
    /// </summary>
    static List<int> ComputeWidths(List<string> headers, List<List<string>> rows, int n)
    {
        const int total = 10200;   // usable width in twips (A4, narrow margins)
        const int padding = 150;   // left + right cell margin
        const int charWidth = 105; // average glyph width at 8.5pt Aptos

        var minWidth = new int[n];
        var weight = new double[n];

        for (int c = 0; c < n; c++)
        {
            // The header word is unbreakable, so it sets the floor.
            var headWords = headers[c].Split(' ', StringSplitOptions.RemoveEmptyEntries);
            int headLongest = headWords.Length == 0 ? 3 : headWords.Max(w => w.Length);

            int dataLongest = 0;
            double avg = 0;
            int sample = 0;
            foreach (var r in rows)
            {
                if (c >= r.Count) continue;
                var cell = r[c];
                foreach (var w in cell.Split(' ', StringSplitOptions.RemoveEmptyEntries))
                    if (w.Length > dataLongest) dataLongest = w.Length;
                avg += Math.Min(cell.Length, 46);
                sample++;
            }

            minWidth[c] = Math.Max(headLongest, dataLongest) * charWidth + padding + 60;
            weight[c] = Math.Max(6.0, Math.Min(avg / Math.Max(1, sample), 46.0));
        }

        // The sign-off column only ever holds a checkbox.
        for (int c = 0; c < n; c++)
        {
            if (headers[c].Equals("Result", StringComparison.OrdinalIgnoreCase))
            {
                minWidth[c] = Math.Max(minWidth[c], 900);
                weight[c] = 5.0;
            }
            if (headers[c].Equals("#", StringComparison.OrdinalIgnoreCase))
            {
                minWidth[c] = Math.Max(minWidth[c], 480);
                weight[c] = 4.0;
            }
            if (headers[c].Equals("Sev", StringComparison.OrdinalIgnoreCase))
            {
                minWidth[c] = Math.Max(minWidth[c], 560);
                weight[c] = 4.5;
            }
            if (headers[c].Equals("Method", StringComparison.OrdinalIgnoreCase))
            {
                minWidth[c] = Math.Max(minWidth[c], 900);
                weight[c] = 6.0;
            }
        }

        // If the floors do not fit, scale them down proportionally.
        int floorSum = minWidth.Sum();
        if (floorSum > total)
        {
            double k = (double)total / floorSum;
            for (int c = 0; c < n; c++) minWidth[c] = Math.Max(260, (int)(minWidth[c] * k));
            floorSum = minWidth.Sum();
        }

        // Distribute whatever is left over by weight.
        int spare = total - floorSum;
        double weightSum = weight.Sum();
        var widths = new List<int>();
        int used = 0;
        for (int c = 0; c < n; c++)
        {
            int extra = c == n - 1 ? spare - used : (int)Math.Round(weight[c] / weightSum * spare);
            int w = minWidth[c] + extra;
            widths.Add(w);
            used += extra;
        }
        widths[n - 1] += total - widths.Sum();
        return widths;
    }
}
