import { jsPDF } from 'jspdf';
import type { SavedFile, AIAnswerBundle } from '../types';

/**
 * Detects if a text is likely Indonesian.
 */
export const isLikelyIndonesianText = (text?: string): boolean => {
  if (!text || !text.trim()) return false;
  const clean = text.toLowerCase().replace(/<[^>]+>/g, ' ');
  const idMarkers = [
    ' yang ', ' dan ', ' di ', ' dari ', ' ini ', ' untuk ', ' pada ', ' adalah ',
    ' dengan ', ' secara ', ' oleh ', ' berdasarkan ', ' langkah ', ' pemerintah ',
    ' kebijakan ', ' kementerian ', ' pemantauan ', ' rekomendasi ', ' hasil ', ' memimpin ',
    ' terkait ', ' keberangkatan ', ' perlindungan '
  ];
  let matches = 0;
  for (const m of idMarkers) {
    if (clean.includes(m)) matches++;
  }
  return matches >= 2;
};

/**
 * Preserves rich text numbering (1., 2., 3.), bullets (•), line breaks,
 * and converts HTML lists (<ol>, <ul>, <li>) into clean numbered or bulleted lines for jsPDF.
 */
export const cleanMarkdownText = (text?: string): string => {
  if (!text) return '-';

  let t = text;

  // 1. Process ordered lists <ol>...</ol> with sequential numbering (1., 2., 3.)
  t = t.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_, listContent) => {
    let itemIdx = 1;
    const items = listContent.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_match: string, itemText: string) => {
      const cleanItem = itemText.replace(/<[^>]+>/g, '').trim();
      return cleanItem ? `\n${itemIdx++}. ${cleanItem}\n` : '';
    });
    return `\n${items}\n`;
  });

  // 2. Process unordered lists <ul>...</ul> with bullets (• )
  t = t.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (_, listContent) => {
    const items = listContent.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_match: string, itemText: string) => {
      const cleanItem = itemText.replace(/<[^>]+>/g, '').trim();
      return cleanItem ? `\n• ${cleanItem}\n` : '';
    });
    return `\n${items}\n`;
  });

  // 3. Process standalone <li>...</li>
  t = t.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, itemText) => {
    const cleanItem = itemText.replace(/<[^>]+>/g, '').trim();
    return cleanItem ? `\n• ${cleanItem}\n` : '';
  });

  // 4. Convert block tags to line breaks
  t = t
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/h[1-6]>/gi, '\n\n');

  // 5. Strip remaining HTML tags
  t = t.replace(/<[^>]+>/g, '');

  // 6. Decode HTML entities
  t = t
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");

  // 7. Markdown list formatting:
  // Normalize markdown bullet lists (* or -) into bullet symbols (• )
  t = t.replace(/^[ \t]*[-*][ \t]+/gm, '• ');

  // Clean Markdown headers #, ##, ###
  t = t.replace(/^[ \t]*#{1,6}[ \t]+/gm, '');

  // Strip Markdown bold and italic markers (**bold** -> bold, *italic* -> italic)
  t = t.replace(/\*\*([^*]+)\*\*/g, '$1');
  t = t.replace(/__([^_]+)__/g, '$1');
  t = t.replace(/```[a-z]*\n?/gi, '');
  t = t.replace(/```/g, '');

  // 8. Normalize spacing and linebreaks
  t = t
    .split('\n')
    .map(line => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return t || '-';
};

/**
 * Resolves the official English version for Card 11 (Jawaban Terpilih).
 * Ensures 100% synchronization with what the user actually selected or edited.
 */
export const resolveEnglishSelectedAnswer = (file: SavedFile): string => {
  const chosen = (file.selected_answer || '').trim();

  // 1. If user selected/edited an answer and it is already in English, use it directly!
  if (chosen && !isLikelyIndonesianText(chosen)) {
    return chosen;
  }

  // 2. If an explicit English translation is saved for this specific selected answer
  if (file.selected_answer_en && file.selected_answer_en.trim() && !isLikelyIndonesianText(file.selected_answer_en)) {
    const isStaleCard3 = file.selected_answer_en.includes('Indonesia consistently upholds') &&
      chosen && !chosen.includes('Indonesia secara konsisten menjunjung');
    if (!isStaleCard3) {
      return file.selected_answer_en.trim();
    }
  }

  const et = file.english_translations;
  if (et) {
    if (et.card_11 && et.card_11.trim() && !isLikelyIndonesianText(et.card_11)) {
      const isStaleCard3 = et.card_11.includes('Indonesia consistently upholds') &&
        chosen && !chosen.includes('Indonesia secara konsisten menjunjung');
      if (!isStaleCard3) {
        return et.card_11.trim();
      }
    }
    if (et.selected_answer && et.selected_answer.trim() && !isLikelyIndonesianText(et.selected_answer)) {
      const isStaleCard3 = et.selected_answer.includes('Indonesia consistently upholds') &&
        chosen && !chosen.includes('Indonesia secara konsisten menjunjung');
      if (!isStaleCard3) {
        return et.selected_answer.trim();
      }
    }
    // Match specific cards from english_translations if chosen contains text from those cards
    const cleanChosen = chosen.toLowerCase();
    const candidateKeys = [
      { id: 'card_13', en: et.card_13, idText: file.chatgpt_answers?.resolution_recommendations },
      { id: 'card_14', en: et.card_14, idText: file.chatgpt_answers?.kemenko_role },
      { id: 'card_17', en: et.card_17, idText: file.gemini_answers?.resolution_recommendations },
      { id: 'card_18', en: et.card_18, idText: file.gemini_answers?.kemenko_role },
      { id: 'card_4', en: et.card_4, idText: file.chatgpt_answers?.concise_answer },
      { id: 'card_9', en: et.card_9, idText: file.gemini_answers?.concise_answer },
      { id: 'card_5', en: et.card_5, idText: file.chatgpt_answers?.brief_analysis },
      { id: 'card_10', en: et.card_10, idText: file.gemini_answers?.brief_analysis },
      { id: 'card_3', en: et.card_3, idText: file.chatgpt_answers?.main_answer },
      { id: 'card_8', en: et.card_8, idText: file.gemini_answers?.main_answer },
    ];
    const matchedEns: string[] = [];
    for (const c of candidateKeys) {
      if (c.en && c.en.trim()) {
        const idSlice = (c.idText || '').trim().slice(0, 25).toLowerCase();
        const enSlice = c.en.trim().slice(0, 25).toLowerCase();
        if ((idSlice.length > 10 && cleanChosen.includes(idSlice)) ||
            (enSlice.length > 10 && cleanChosen.includes(enSlice))) {
          matchedEns.push(c.en.trim());
        }
      }
    }
    if (matchedEns.length > 0) {
      return matchedEns.join('\n\n');
    }
  }

  // 3. Fallback to chosen text
  return chosen || file.selected_answer_en || '-';
};


/**
 * Internal renderer that outputs ALL on-point cards into a clean, official jsPDF document.
 * Strictly avoids any AI engine branding ("ChatGPT", "Gemini", "generate AI") and uses exact on-point titles.
 * Displays all contents of every box (Kolom 1, Kolom 2, Judul, Jawaban Terpilih, Catatan) with full pagination.
 */
const renderFullSessionCards = (
  doc: jsPDF,
  file: SavedFile,
  _index: number = 0,
  _totalFiles: number = 1
) => {
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;
  const contentWidth = pageWidth - (margin * 2);
  let y = margin;

  const checkPageBreak = (neededHeight: number) => {
    if (y + neededHeight > pageHeight - margin - 12) {
      doc.addPage();
      y = margin;
    }
  };

  // 1. Official Header Banner (Dialogue AI Representative saja)
  doc.setFillColor(15, 23, 42); // Dark slate #0F172A
  doc.rect(margin, y, contentWidth, 11, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  doc.text('DIALOGUE AI REPRESENTATIVE', margin + 6, y + 7.5);
  y += 16;

  // 2. Judul Dokumen (Kotak Judul)
  if (file.title && file.title.trim()) {
    checkPageBreak(14);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    const titleLines = doc.splitTextToSize(cleanMarkdownText(file.title), contentWidth);
    for (const line of titleLines) {
      if (y + 5 > pageHeight - margin - 12) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += 5.2;
    }
    y += 4;
  }

  // Section Header Renderer
  const renderSectionHeader = (label: string, isHighlight = false) => {
    checkPageBreak(16);

    if (isHighlight) {
      doc.setFillColor(37, 99, 235); // Blue banner #2563EB
      doc.rect(margin, y, contentWidth, 7, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(255, 255, 255);
      doc.text(label, margin + 4, y + 4.8);
      y += 9.5;
    } else {
      doc.setFillColor(241, 245, 249); // Light slate #F1F5F9
      doc.rect(margin, y, contentWidth, 6, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(30, 41, 59);
      doc.text(label, margin + 4, y + 4.2);
      y += 8.5;
    }
  };

  // Robust Text Block Renderer with Line-by-Line Pagination
  const renderTextBlock = (
    text: string,
    options: {
      isItalic?: boolean;
      isBold?: boolean;
      isHighlight?: boolean;
    } = {}
  ) => {
    const cleanText = cleanMarkdownText(text);
    if (!cleanText || cleanText === '-') return;

    doc.setFont('helvetica', options.isItalic ? 'italic' : (options.isBold ? 'bold' : 'normal'));
    doc.setFontSize(8);
    doc.setTextColor(options.isHighlight ? 15 : 51, options.isHighlight ? 23 : 65, options.isHighlight ? 42 : 85);

    const lines = doc.splitTextToSize(cleanText, contentWidth - 8);
    const lineHeight = 4.2;

    for (let i = 0; i < lines.length; i++) {
      if (y + lineHeight > pageHeight - margin - 12) {
        doc.addPage();
        y = margin;
      }
      doc.text(lines[i], margin + 4, y);
      y += lineHeight;
    }
    y += 2.5;
  };

  // Topic Renderer that outputs ALL boxes (Kolom 1 & Kolom 2)
  const renderTopic = (
    label: string,
    box1?: string | null,
    box2?: string | null,
    options: {
      isItalic?: boolean;
      isBold?: boolean;
      isHighlight?: boolean;
    } = {}
  ) => {
    const b1 = (box1 || '').trim();
    const b2 = (box2 || '').trim();

    const clean1 = cleanMarkdownText(b1);
    const clean2 = cleanMarkdownText(b2);

    const has1 = clean1 !== '-' && clean1.length > 0;
    const has2 = clean2 !== '-' && clean2.length > 0;

    if (!has1 && !has2) return;

    renderSectionHeader(label, options.isHighlight);

    if (has1 && has2) {
      const norm1 = clean1.replace(/\s+/g, ' ').toLowerCase();
      const norm2 = clean2.replace(/\s+/g, ' ').toLowerCase();

      if (norm1 === norm2) {
        // Exactly identical: render once
        renderTextBlock(b1, options);
      } else {
        // Both boxes have distinct content: render BOTH!
        renderTextBlock(b1, options);

        // Clean subtle divider between box 1 and box 2
        checkPageBreak(7);
        doc.setDrawColor(226, 232, 240);
        doc.setLineWidth(0.3);
        doc.line(margin + 4, y, margin + contentWidth - 4, y);
        y += 4;

        renderTextBlock(b2, options);
      }
    } else if (has1) {
      renderTextBlock(b1, options);
    } else if (has2) {
      renderTextBlock(b2, options);
    }

    y += 3; // Section spacing
  };

  const cg = (file.chatgpt_answers || {}) as Partial<AIAnswerBundle>;
  const gm = (file.gemini_answers || {}) as Partial<AIAnswerBundle>;
  const ai = (file.ai_answers || {}) as Partial<AIAnswerBundle>;

  // 1. Pertanyaan Asli
  renderTopic(
    'Pertanyaan Asli',
    (cg as any).original_audio_text || file.original_audio_text,
    (gm as any).original_audio_text || file.original_audio_text,
    { isItalic: true }
  );

  // 2. Terjemahan Bahasa Indonesia
  renderTopic(
    'Terjemahan Bahasa Indonesia',
    (cg as any).translated_indonesian_text || file.translated_indonesian_text,
    (gm as any).translated_indonesian_text || file.translated_indonesian_text,
    { isBold: true }
  );

  // 3. Jawaban Utama
  renderTopic('Jawaban Utama', cg.main_answer || ai.main_answer, gm.main_answer);

  // 4. Jawaban Singkat
  renderTopic('Jawaban Singkat', cg.concise_answer || ai.concise_answer, gm.concise_answer);

  // 5. Analisis
  renderTopic('Analisis', cg.brief_analysis || ai.brief_analysis, gm.brief_analysis);

  // 6. Masalah dan Hasil Pemantauan
  renderTopic('Masalah dan Hasil Pemantauan', cg.monitoring_issues || ai.monitoring_issues, gm.monitoring_issues);

  // 7. Rekomendasi Penyelesaian
  renderTopic('Rekomendasi Penyelesaian', cg.resolution_recommendations || ai.resolution_recommendations, gm.resolution_recommendations);

  // 8. Peran Kemenkopolkam
  renderTopic('Peran Kemenkopolkam', cg.kemenko_role || ai.kemenko_role, gm.kemenko_role);

  // 9. Usulan Agenda Pemantauan Lapangan
  renderTopic('Usulan Agenda Pemantauan Lapangan', cg.field_monitoring_agenda || ai.field_monitoring_agenda, gm.field_monitoring_agenda);

  // 10. Berita Terbaru
  renderTopic('Berita Terbaru', cg.latest_news || ai.latest_news, gm.latest_news);

  // 11. Jawaban Terpilih (English Version)
  const englishSelectedAnswer = resolveEnglishSelectedAnswer(file);
  renderTopic(
    'Jawaban Terpilih',
    englishSelectedAnswer,
    null,
    { isHighlight: true, isBold: true }
  );

  // Rujukan Bahasa Indonesia jika pilihan asli memang berbahasa Indonesia
  if (file.selected_answer && file.selected_answer.trim()) {
    const isIndo = isLikelyIndonesianText(file.selected_answer);
    const cleanSel = cleanMarkdownText(file.selected_answer);
    const cleanEn = cleanMarkdownText(englishSelectedAnswer);
    if (isIndo && cleanSel.toLowerCase() !== cleanEn.toLowerCase()) {
      renderTopic('Rujukan Jawaban Terpilih (Bahasa Indonesia)', `"${cleanSel}"`, null, { isItalic: true });
    }
  }

  // 12. Catatan
  if (file.notes && file.notes.trim()) {
    renderTopic('Catatan', file.notes, null);
  }
};

/**
 * Builds the official jsPDF instance for a single session file containing ALL cards and English Card 11.
 */
export const buildSingleSessionPdfDoc = (file: SavedFile): jsPDF => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  renderFullSessionCards(doc, file, 0, 1);

  // Footer on each page
  const totalPages = (doc as any).internal.getNumberOfPages();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;

  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text('Dialogue AI Representative', margin, pageHeight - 7);
    doc.text(`Halaman ${i} dari ${totalPages}`, pageWidth - margin - 24, pageHeight - 7);
  }

  return doc;
};

/**
 * Exports a single documented session file to an official formatted PDF.
 */
export const exportSingleSessionPdf = (file: SavedFile) => {
  const doc = buildSingleSessionPdfDoc(file);
  const safeFilename = `Dialogue_AI_${(file.id || 'dokumen').replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`;
  doc.save(safeFilename);
};

/**
 * Builds the official jsPDF instance for all selected session files into a combined multi-page report PDF.
 */
export const buildAllSessionsPdfDoc = (files: SavedFile[]): jsPDF => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  if (files.length === 0) return doc;

  files.forEach((file, index) => {
    if (index > 0) {
      doc.addPage();
    }
    renderFullSessionCards(doc, file, index, files.length);
  });

  // Footer on all pages
  const totalPages = (doc as any).internal.getNumberOfPages();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;

  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text('Dialogue AI Representative', margin, pageHeight - 7);
    doc.text(`Halaman ${i} dari ${totalPages}`, pageWidth - margin - 24, pageHeight - 7);
  }

  return doc;
};

/**
 * Exports all documented session files into a combined multi-page report PDF.
 */
export const exportAllSessionsPdf = (files: SavedFile[]) => {
  if (files.length === 0) return;
  const doc = buildAllSessionsPdfDoc(files);
  const dateStr = new Date().toISOString().split('T')[0];
  doc.save(`Dialogue_AI_Dokumen_Resmi_${dateStr}.pdf`);
};

/**
 * Generates identical official PDF base64 payload from selected sessions for direct extraction & display in Teleprompter.
 */
export const generatePdfBase64FromSessions = (files: SavedFile[]): { filename: string; base64: string } => {
  if (files.length === 0) throw new Error('Tidak ada dokumen yang dipilih');
  const doc = files.length === 1 ? buildSingleSessionPdfDoc(files[0]) : buildAllSessionsPdfDoc(files);
  const filename = files.length === 1
    ? `Dialogue_AI_${(files[0].id || 'dokumen').replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`
    : `Dialogue_AI_Prompter_(${files.length}_Dokumen).pdf`;

  const dataUri = doc.output('datauristring');
  const base64 = dataUri.split(',')[1] || dataUri;
  return { filename, base64 };
};
