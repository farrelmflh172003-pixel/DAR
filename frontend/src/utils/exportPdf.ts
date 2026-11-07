import { jsPDF } from 'jspdf';
import type { SavedFile } from '../types';

/**
 * Builds the official jsPDF instance for a single session file.
 */
export const buildSingleSessionPdfDoc = (file: SavedFile): jsPDF => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;
  const contentWidth = pageWidth - (margin * 2);
  let y = margin;

  const checkPageBreak = (neededHeight: number) => {
    if (y + neededHeight > pageHeight - margin - 14) {
      doc.addPage();
      y = margin;
    }
  };

  // 1. Official Header
  doc.setFillColor(15, 23, 42); // Dark slate header #0F172A
  doc.rect(margin, y, contentWidth, 18, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('KEMENTERIAN KOORDINATOR BIDANG POLITIK DAN KEAMANAN RI', margin + 6, y + 7);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(203, 213, 225);
  doc.text('MENKOPOLKAM AI HUB — DOKUMEN ARSIP RESMI SESI DIPLOMASI', margin + 6, y + 13);
  y += 24;

  // 2. Title & ID
  doc.setTextColor(15, 23, 42);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  const titleLines = doc.splitTextToSize(file.title || 'Dokumen Sesi Tanpa Judul', contentWidth);
  doc.text(titleLines, margin, y);
  y += (titleLines.length * 6) + 4;

  // 3. Metadata Table Box
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.rect(margin, y, contentWidth, 23, 'FD');

  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(71, 85, 105);
  doc.text('ID DOKUMEN:', margin + 4, y + 6);
  doc.text('WAKTU / SESI:', margin + 4, y + 12);
  doc.text('PENANYA / DELEGASI:', margin + 4, y + 18);

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(15, 23, 42);
  doc.text(file.id || '-', margin + 36, y + 6);
  doc.text(file.timestamp || '-', margin + 36, y + 12);
  doc.text(file.speaker || 'Delegasi / Penanya', margin + 36, y + 18);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(71, 85, 105);
  doc.text('BAHASA ASLI:', margin + 102, y + 6);
  doc.text('TANGGAL ARSIP:', margin + 102, y + 12);

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(15, 23, 42);
  doc.text(file.detected_language_name || file.detected_language || 'Otomatis', margin + 130, y + 6);
  doc.text(file.updated_at || file.created_at || '-', margin + 130, y + 12);

  y += 29;

  // Section Block Helper
  const addSection = (label: string, text: string, isItalic = false, isBold = false) => {
    checkPageBreak(25);
    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, contentWidth, 6.5, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.setTextColor(30, 41, 59);
    doc.text(label, margin + 4, y + 4.6);
    y += 9.5;

    doc.setFont('helvetica', isItalic ? 'italic' : (isBold ? 'bold' : 'normal'));
    doc.setFontSize(8.5);
    doc.setTextColor(51, 65, 85);

    const cleanText = text
      ? text
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<\/p>/gi, '\n')
          .replace(/<\/div>/gi, '\n')
          .replace(/<[^>]+>/g, '')
          .replace(/&nbsp;/g, ' ')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/\*\*/g, '')
          .replace(/###/g, '')
          .replace(/```/g, '')
          .trim()
      : '-';
    const lines = doc.splitTextToSize(cleanText, contentWidth - 8);
    checkPageBreak(lines.length * 4.6 + 6);
    doc.text(lines, margin + 4, y);
    y += (lines.length * 4.6) + 6;
  };

  // Section 1: Tangkapan Suara Asing
  addSection('1. TANGKAPAN SUARA ASING (STT ORIGINAL)', `"${file.original_audio_text || '-'}"`, true);

  // Section 2: Terjemahan 100% Bahasa Indonesia
  addSection('2. HASIL TRANSLATE BAHASA INDONESIA (100% TERJEMAHAN)', `"${file.translated_indonesian_text || '-'}"`, false, true);

  // Section 3: Jawaban Utama AI
  addSection('3. GENERATE AI — JAWABAN UTAMA', file.ai_answers?.main_answer || file.selected_answer || '-');

  // Section 4: Jawaban Singkat AI
  addSection('4. GENERATE AI — JAWABAN SINGKAT', file.ai_answers?.concise_answer || '-');

  // Section 5: Jawaban Analisis AI
  addSection('5. GENERATE AI — JAWABAN ANALISIS STRATEGIS', file.ai_answers?.brief_analysis || '-');

  if (file.ai_answers?.monitoring_issues) {
    addSection('6. MASALAH DAN HASIL PEMANTAUAN', file.ai_answers.monitoring_issues);
  }
  if (file.ai_answers?.resolution_recommendations) {
    addSection('7. REKOMENDASI PENYELESAIAN', file.ai_answers.resolution_recommendations);
  }
  if (file.ai_answers?.kemenko_role) {
    addSection('8. PERAN KEMENKO POLKAM', file.ai_answers.kemenko_role);
  }
  if (file.ai_answers?.field_monitoring_agenda) {
    addSection('9. USULAN AGENDA PEMANTAUAN LAPANGAN', file.ai_answers.field_monitoring_agenda);
  }
  if (file.ai_answers?.latest_news || file.chatgpt_answers?.latest_news || file.gemini_answers?.latest_news) {
    addSection('10. BERITA TERBARU', file.ai_answers?.latest_news || file.chatgpt_answers?.latest_news || file.gemini_answers?.latest_news || '-');
  }
  if (file.selected_answer) {
    addSection('11. JAWABAN TERPILIH', file.selected_answer, false, true);
  }

  if (file.notes) {
    addSection('CATATAN KHUSUS OPERATOR', file.notes);
  }

  // Footer on each page
  const totalPages = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text('Dokumen ini dicatat dan didokumentasikan secara otomatis oleh Sistem MENKOPOLKAM AI HUB.', margin, pageHeight - 7);
    doc.text(`Halaman ${i} dari ${totalPages}`, pageWidth - margin - 24, pageHeight - 7);
  }

  return doc;
};

/**
 * Exports a single documented session file to an official formatted PDF.
 */
export const exportSingleSessionPdf = (file: SavedFile) => {
  const doc = buildSingleSessionPdfDoc(file);
  const safeFilename = `Menkopolkam-${(file.id || 'dokumen').replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`;
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

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 16;
  const contentWidth = pageWidth - (margin * 2);

  files.forEach((file, index) => {
    if (index > 0) {
      doc.addPage();
    }
    let y = margin;

    const checkPageBreak = (neededHeight: number) => {
      if (y + neededHeight > pageHeight - margin - 14) {
        doc.addPage();
        y = margin;
      }
    };

    // Header
    doc.setFillColor(15, 23, 42);
    doc.rect(margin, y, contentWidth, 18, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.text('KEMENTERIAN KOORDINATOR BIDANG POLITIK DAN KEAMANAN RI', margin + 6, y + 7);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(203, 213, 225);
    doc.text(`MENKOPOLKAM AI HUB — LAPORAN DOKUMEN ARSIP #${index + 1} DARI ${files.length}`, margin + 6, y + 13);
    y += 24;

    // Title
    doc.setTextColor(15, 23, 42);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    const titleLines = doc.splitTextToSize(file.title || 'Dokumen Sesi', contentWidth);
    doc.text(titleLines, margin, y);
    y += (titleLines.length * 6) + 3;

    // Metadata
    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.rect(margin, y, contentWidth, 20, 'FD');

    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(71, 85, 105);
    doc.text('ID DOKUMEN:', margin + 4, y + 6);
    doc.text('WAKTU:', margin + 4, y + 12);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(15, 23, 42);
    doc.text(file.id || '-', margin + 30, y + 6);
    doc.text(file.timestamp || '-', margin + 30, y + 12);

    doc.setFont('helvetica', 'bold');
    doc.setTextColor(71, 85, 105);
    doc.text('BAHASA:', margin + 95, y + 6);
    doc.text('PENANYA:', margin + 95, y + 12);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(15, 23, 42);
    doc.text(file.detected_language_name || file.detected_language || '-', margin + 115, y + 6);
    doc.text(file.speaker || 'Delegasi / Penanya', margin + 115, y + 12);

    y += 26;

    const addSection = (label: string, text: string, isItalic = false, isBold = false) => {
      checkPageBreak(22);
      doc.setFillColor(241, 245, 249);
      doc.rect(margin, y, contentWidth, 6, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(30, 41, 59);
      doc.text(label, margin + 4, y + 4.5);
      y += 8.5;

      doc.setFont('helvetica', isItalic ? 'italic' : (isBold ? 'bold' : 'normal'));
      doc.setFontSize(8);
      doc.setTextColor(51, 65, 85);

      const cleanText = text
        ? text
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/<\/p>/gi, '\n')
            .replace(/<\/div>/gi, '\n')
            .replace(/<[^>]+>/g, '')
            .replace(/&nbsp;/g, ' ')
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/\*\*/g, '')
            .replace(/###/g, '')
            .replace(/```/g, '')
            .trim()
        : '-';
      const lines = doc.splitTextToSize(cleanText, contentWidth - 8);
      checkPageBreak(lines.length * 4.4 + 5);
      doc.text(lines, margin + 4, y);
      y += (lines.length * 4.4) + 5;
    };

    addSection('1. TANGKAPAN SUARA ASING (STT ORIGINAL)', `"${file.original_audio_text || '-'}"`, true);
    addSection('2. TERJEMAHAN 100% BAHASA INDONESIA', `"${file.translated_indonesian_text || '-'}"`, false, true);
    addSection('3. JAWABAN UTAMA AI', file.ai_answers?.main_answer || file.selected_answer || '-');
    addSection('4. JAWABAN SINGKAT AI', file.ai_answers?.concise_answer || '-');
    addSection('5. ANALISIS STRATEGIS AI', file.ai_answers?.brief_analysis || '-');
    if (file.ai_answers?.monitoring_issues) {
      addSection('6. MASALAH DAN HASIL PEMANTAUAN', file.ai_answers.monitoring_issues);
    }
    if (file.ai_answers?.resolution_recommendations) {
      addSection('7. REKOMENDASI PENYELESAIAN', file.ai_answers.resolution_recommendations);
    }
    if (file.ai_answers?.kemenko_role) {
      addSection('8. PERAN KEMENKO POLKAM', file.ai_answers.kemenko_role);
    }
    if (file.ai_answers?.field_monitoring_agenda) {
      addSection('9. USULAN AGENDA PEMANTAUAN LAPANGAN', file.ai_answers.field_monitoring_agenda);
    }
    if (file.ai_answers?.latest_news || file.chatgpt_answers?.latest_news || file.gemini_answers?.latest_news) {
      addSection('10. BERITA TERBARU', file.ai_answers?.latest_news || file.chatgpt_answers?.latest_news || file.gemini_answers?.latest_news || '-');
    }
    if (file.selected_answer) {
      addSection('11. JAWABAN TERPILIH', file.selected_answer, false, true);
    }
  });

  // Footer on all pages
  const totalPages = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text('Kemenko Polkam RI — Laporan Terkonsolidasi Menkopolkam AI Hub.', margin, pageHeight - 7);
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
  doc.save(`Menkopolkam-Semua-Dokumen-Arsip-${dateStr}.pdf`);
};

/**
 * Generates identical official PDF base64 payload from selected sessions for direct extraction & display in Teleprompter.
 */
export const generatePdfBase64FromSessions = (files: SavedFile[]): { filename: string; base64: string } => {
  if (files.length === 0) throw new Error('Tidak ada dokumen yang dipilih');
  const doc = files.length === 1 ? buildSingleSessionPdfDoc(files[0]) : buildAllSessionsPdfDoc(files);
  const filename = files.length === 1
    ? `Menkopolkam-${(files[0].id || 'dokumen').replace(/[^a-zA-Z0-9_-]/g, '_')}.pdf`
    : `Menkopolkam-Export-Prompter-(${files.length}-Dokumen).pdf`;

  const dataUri = doc.output('datauristring');
  const base64 = dataUri.split(',')[1] || dataUri;
  return { filename, base64 };
};
