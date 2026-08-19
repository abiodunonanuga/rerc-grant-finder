#!/usr/bin/env python3
"""Apply the reviewed August 2026 resource, case-study, and Word-export updates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"Expected one {label} block, found {text.count(old)}")
    return text.replace(old, new, 1)


def update_planner() -> None:
    path = ROOT / "planner.js"
    text = path.read_text(encoding="utf-8")

    helper_anchor = '''  function docxPageBreak() {
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>';
  }
'''
    helpers = '''  function docxRichParagraph(parts, style) {
    const styleXml = style ? '<w:pPr><w:pStyle w:val="' + xmlEscape(style) + '"/></w:pPr>' : "";
    const runs = parts.map(function (part) {
      const properties = [];
      if (part.bold) properties.push("<w:b/>");
      if (part.italic) properties.push("<w:i/>");
      return "<w:r>" + (properties.length ? "<w:rPr>" + properties.join("") + "</w:rPr>" : "") +
        '<w:t xml:space="preserve">' + xmlEscape(part.text) + "</w:t></w:r>";
    }).join("");
    return "<w:p>" + styleXml + runs + "</w:p>";
  }

  function docxKeyValue(label, value) {
    return docxRichParagraph([{ text: label + ": ", bold: true }, { text: value }], "KeyValue");
  }

''' + helper_anchor
    text = replace_once(text, helper_anchor, helpers, "DOCX helper")

    intro_old = '''    body.push(docxParagraph(model.title, "Title"));
    body.push(docxParagraph(t("communitySnapshot"), "Heading1"));
    profileRows(model.profile).forEach(function (row) {
      body.push(docxParagraph(row.label + ": " + row.value));
    });
    if (model.notes) {
      body.push(docxParagraph(t("projectNotesHeading"), "Heading1"));
      model.notes.split(/\\r?\\n/).forEach(function (line) { body.push(docxParagraph(line || " ")); });
    }
    body.push(docxParagraph(t("roadmap"), "Heading1"));
'''
    intro_new = '''    body.push(docxParagraph(model.title, "Title"));
    body.push(docxParagraph("Recreation Economy for Rural Communities", "Subtitle"));
    body.push(docxParagraph(t("prepared", { date: new Date().toLocaleDateString(state.language === "es" ? "es-US" : "en-US") }), "Metadata"));
    body.push(docxParagraph(t("communitySnapshot"), "Heading1"));
    profileRows(model.profile).forEach(function (row) {
      body.push(docxKeyValue(row.label, row.value));
    });
    if (model.notes) {
      body.push(docxParagraph(t("projectNotesHeading"), "Heading1"));
      model.notes.split(/\\r?\\n/).forEach(function (line) { body.push(docxParagraph(line || " ", "BodyText")); });
    }
    body.push(docxParagraph(t("roadmap"), "Heading1"));
    body.push(docxParagraph(t(model.items.length === 1 ? "selectedItemSummary" : "selectedItemsSummary", { count: model.items.length }), "Metadata"));
'''
    if 'body.push(docxParagraph("Recreation Economy for Rural Communities", "Subtitle"));' not in text:
        intro_start = text.index('    body.push(docxParagraph(model.title, "Title"));')
        intro_end = text.index('    PHASES.forEach(function (phase) {', intro_start)
        text = text[:intro_start] + intro_new + text[intro_end:]

    item_old = '''        body.push(docxPageBreak());
        body.push(docxParagraph(t(phase.toLowerCase()), "Heading2"));
        body.push(docxParagraph(textValue(item.title, 500), "Heading3"));
        [
          [t("organization"), item.organization],
          [t("type"), item.item_type],
          [t("status"), item.status],
          [t("applicant"), item.eligible_users],
          [t("geography"), item.geography],
          [t("stage"), item.project_stage],
          [t("amount"), item.amount_or_cost],
          [t("match"), item.match_or_cost],
          [t("deadline"), item.deadline_or_availability],
        ].forEach(function (row) {
          if (row[1]) body.push(docxParagraph(row[0] + ": " + row[1]));
        });
        body.push(docxParagraph(summaryFor(item)));
        const source = safeHttpUrl(item.source_url);
        if (source) {
          const relationshipId = "rId" + (relationships.length + 1);
          relationships.push({ id: relationshipId, url: source });
          body.push(docxParagraph(t("openSource"), "", relationshipId));
        }
'''
    item_new = '''        body.push(docxPageBreak());
        body.push(docxParagraph(t(item.item_type === "Funding" ? "fundingCategory" : item.item_type === "Resource" ? "resourceCategory" : "caseStudyCategory").toUpperCase(), "Category"));
        body.push(docxParagraph(t("phaseLabel", { phase: t(phase.toLowerCase()) }), "PhaseLabel"));
        body.push(docxParagraph(textValue(item.title, 500), "Heading2"));
        [
          [t("organization"), item.organization],
          [t("status"), item.status],
          [t("applicant"), item.eligible_users],
          [t("geography"), item.geography],
          [t("stage"), item.project_stage],
          [t("amount"), item.amount_or_cost],
          [t("match"), item.match_or_cost],
          [t("deadline"), item.deadline_or_availability],
        ].forEach(function (row) {
          if (row[1]) body.push(docxKeyValue(row[0], row[1]));
        });
        body.push(docxParagraph(t("overviewHeading"), "Heading3"));
        body.push(docxParagraph(summaryFor(item), "BodyText"));
        const source = safeHttpUrl(item.source_url);
        if (source) {
          const relationshipId = "rId" + (relationships.length + 1);
          relationships.push({ id: relationshipId, url: source });
          body.push(docxParagraph(t("openSource"), "SourceLink", relationshipId));
        }
'''
    if 'body.push(docxParagraph(t(item.item_type === "Funding" ? "fundingCategory" : item.item_type === "Resource" ? "resourceCategory" : "caseStudyCategory").toUpperCase(), "Category"));' not in text:
        item_start = text.index('        body.push(docxPageBreak());')
        item_end = text.index('      });\n    });', item_start)
        text = text[:item_start] + item_new + text[item_end:]
    text = replace_once(
        text,
        '    body.push(docxParagraph(t("officialEnglish")));',
        '    body.push(docxParagraph(t("officialEnglish"), "ClosingNote"));',
        "DOCX footer",
    )

    style_start = text.index('    const documentLanguage = state.language === "es" ? "es-ES" : "en-US";\n    const stylesXml =')
    style_end = text.index("    const zip = new window.JSZip();", style_start)
    styles = '''    const documentLanguage = state.language === "es" ? "es-ES" : "en-US";
    const stylesXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
      '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="21"/><w:color w:val="24352F"/><w:lang w:val="' + documentLanguage + '"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="38"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:i/><w:color w:val="4D6159"/><w:sz w:val="24"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Metadata"><w:name w:val="Metadata"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:color w:val="61736C"/><w:sz w:val="19"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="0"/><w:spacing w:before="240" w:after="100"/><w:pBdr><w:bottom w:val="single" w:sz="12" w:color="D6A525"/></w:pBdr></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="28"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="1"/><w:spacing w:before="160" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="175641"/><w:sz w:val="28"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:qFormat/>' +
      '<w:pPr><w:keepNext/><w:outlineLvl w:val="2"/><w:spacing w:before="160" w:after="60"/></w:pPr><w:rPr><w:b/><w:color w:val="314A41"/><w:sz w:val="22"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Category"><w:name w:val="Category"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="175641"/><w:spacing w:after="80"/><w:ind w:left="120"/></w:pPr><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="PhaseLabel"><w:name w:val="Phase Label"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:color w:val="8A6B16"/><w:sz w:val="19"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="KeyValue"><w:name w:val="Key Value"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="60"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="BodyText"><w:name w:val="Body Text"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:after="160"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="SourceLink"><w:name w:val="Source Link"/><w:basedOn w:val="Normal"/>' +
      '<w:pPr><w:spacing w:before="120"/></w:pPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="ClosingNote"><w:name w:val="Closing Note"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:i/><w:color w:val="61736C"/><w:sz w:val="18"/></w:rPr></w:style>' +
      '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>' +
      '<w:rPr><w:color w:val="1B6A8F"/><w:u w:val="single"/></w:rPr></w:style></w:styles>';
'''
    text = text[:style_start] + styles + text[style_end:]
    path.write_text(text, encoding="utf-8", newline="\n")


def update_translation() -> None:
    path = ROOT / "ui-i18n.js"
    text = path.read_text(encoding="utf-8")
    anchor = '    "All matches": "Todas las opciones",\n'
    additions = anchor + '''    "Resource type": "Tipo de recurso",
    "Technical assistance": "Asistencia técnica",
    "Guides and toolkits": "Guías y herramientas",
    "Data, maps, and calculators": "Datos, mapas y calculadoras",
    "Training and webinars": "Capacitación y seminarios web",
    "Directories and resource hubs": "Directorios y centros de recursos",
    "Reports and research": "Informes e investigación",
    "Case studies shown": "Casos prácticos mostrados",
    "Featured matches (24)": "Opciones destacadas (24)",
    "More matches (60)": "Más opciones (60)",
    "Expanded matches (120)": "Opciones ampliadas (120)",
    "Other resources": "Otros recursos",
    "Disaster, water, and resilience": "Desastres, agua y resiliencia",
    "Featured community examples": "Ejemplos comunitarios destacados",
    "Open the Case studies tab for more ranked examples and links to complete source libraries.": "Abra la pestaña Casos prácticos para ver más ejemplos clasificados y enlaces a bibliotecas completas.",
    "Open resource": "Abrir recurso",
    "Case study libraries": "Bibliotecas de casos prácticos",
    "Browse full case study collections": "Explore colecciones completas de casos prácticos",
    "Use the ranked examples below, or search a complete source library.": "Use los ejemplos clasificados a continuación o busque en una biblioteca completa.",
    "EPA Smart Growth examples": "Ejemplos de Crecimiento Inteligente de EPA",
    "EPA Brownfields success stories": "Historias de éxito de Brownfields de EPA",
    "U.S. Climate Resilience Toolkit case studies": "Casos prácticos del Kit de Resiliencia Climática de EE. UU.",
    "USDA Rural Development success stories": "Historias de éxito de Desarrollo Rural de USDA",
'''
    text = replace_once(text, anchor, additions, "Spanish usability translations")
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    update_planner()
    update_translation()
    print("Applied RERC usability feedback integration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
