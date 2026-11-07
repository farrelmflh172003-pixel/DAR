import React from 'react';
import { 
  Mic, 
  Ear, 
  Languages, 
  Sparkles, 
  Square, 
  PlusCircle,
  FolderOpen,
  Save
} from 'lucide-react';

export type WorkflowStage = 
  | 'idle' 
  | 'listening' 
  | 'transcribing' 
  | 'processing' 
  | 'completed';

interface WorkflowBarProps {
  currentStage: WorkflowStage;
  isRecording: boolean;
  isProcessing: boolean;
  hasData: boolean;
  savedCount: number;
  onToggleMic: () => void;
  onOffMic: () => void;
  onOpenSavedFiles: () => void;
  onNewFile: () => void;
  onManualSave?: () => void;
  isSaving?: boolean;
}

export const WorkflowBar: React.FC<WorkflowBarProps> = ({
  currentStage,
  isRecording,
  isProcessing,
  hasData,
  savedCount,
  onToggleMic,
  onOffMic,
  onOpenSavedFiles,
  onNewFile,
  onManualSave,
  isSaving = false
}) => {
  return (
    <div className={`flow-pipeline-bar stage-${currentStage}`} role="region" aria-label="Alur Diplomasi Sesuai Diagram">
      <div className="flow-steps-track">
        {/* Step 1: On Mic */}
        <button
          type="button"
          onClick={onToggleMic}
          className={`flow-step-node ${isRecording ? 'node-active' : ''}`}
          title={isRecording ? "Klik untuk Matikan Mic & Proses AI" : "Klik untuk Menyalakan Mic (On Mic)"}
        >
          <div className="flow-node-icon">
            <Mic size={13} className={isRecording ? "text-emerald-400 animate-pulse" : "text-zinc-400"} />
          </div>
          <span className="flow-node-label font-bold">
            {isRecording ? "MIC AKTIF (ON)" : "ON MIC"}
          </span>
        </button>

        <span className={`flow-connector ${isRecording ? 'connector-active' : ''}`}>→</span>

        {/* Step 2: Mendengarkan */}
        <div className={`flow-step-node ${isRecording ? 'node-active' : ''}`}>
          <div className="flow-node-icon">
            <Ear size={13} className={isRecording ? "text-blue-400 animate-pulse" : "text-zinc-500"} />
          </div>
          <span className="flow-node-label">Mendengarkan</span>
        </div>

        <span className={`flow-connector ${isRecording ? 'connector-active' : ''}`}>→</span>

        {/* Step 3: Menulis Ulang Tangkapan Suara (Asing) */}
        <div className={`flow-step-node ${isRecording || hasData ? 'node-active' : ''}`}>
          <div className="flow-node-icon">
            <Languages size={13} className={isRecording || hasData ? "text-cyan-400" : "text-zinc-500"} />
          </div>
          <span className="flow-node-label">Tangkapan Suara (Asing)</span>
        </div>

        <span className={`flow-connector ${isProcessing || hasData ? 'connector-active' : ''}`}>→</span>

        {/* Step 4: Translate Indo 100% & Generate AI (Utama, Singkat, Analisis) */}
        <button
          type="button"
          onClick={isRecording ? onOffMic : undefined}
          className={`flow-step-node ${isProcessing ? 'node-processing' : (isRecording ? 'node-generate-ready' : (hasData ? 'node-completed' : ''))}`}
          title={isRecording ? "Klik untuk proses AI dan Terjemahan sekarang" : "Status Pemrosesan AI"}
        >
          <div className="flow-node-icon">
            <Sparkles size={13} className={isProcessing ? "text-amber-400 animate-spin" : (isRecording ? "text-indigo-400" : (hasData ? "text-indigo-400" : "text-zinc-500"))} />
          </div>
          <span className="flow-node-label font-bold">
            {isProcessing ? "Memproses AI..." : (isRecording ? "⚡ PROSES AI SEKARANG" : "Translate 100% + Jawaban AI")}
          </span>
        </button>

        <span className={`flow-connector ${!isRecording && hasData ? 'connector-active' : ''}`}>→</span>

        {/* Step 5: Off Mic */}
        <button
          type="button"
          onClick={onOffMic}
          disabled={!isRecording && !hasData}
          className={`flow-step-node ${isRecording ? 'node-off-active cursor-pointer' : (!isRecording && hasData ? 'node-completed' : '')}`}
          title={isRecording ? "Klik untuk Matikan Mic & Generate Respons AI (Off Mic)" : "Status: Mikrofon Mati (Off)"}
        >
          <div className="flow-node-icon">
            <Square size={12} className={isRecording ? "text-rose-400 fill-current animate-pulse" : (!isRecording && hasData ? "text-emerald-400" : "text-zinc-500")} />
          </div>
          <span className="flow-node-label font-bold">
            {isRecording ? "OFF MIC (PROSES AI)" : "Off Mic"}
          </span>
        </button>

        {/* Tombol Save saat mic mati sesuai permintaan user */}
        {!isRecording && onManualSave && (
          <>
            <span className={`flow-connector ${hasData ? 'connector-active' : ''}`}>→</span>
            <button
              type="button"
              onClick={onManualSave}
              disabled={!hasData || isSaving}
              className={`flow-step-node node-save-active ${hasData ? 'cursor-pointer' : 'opacity-60 cursor-not-allowed'}`}
              title="Simpan data sesi ini ke Saved Files"
            >
              <div className="flow-node-icon">
                <Save size={13} className="text-emerald-400" />
              </div>
              <span className="flow-node-label font-bold text-emerald-300">
                {isSaving ? "Menyimpan..." : "SAVE"}
              </span>
            </button>
          </>
        )}
      </div>

      {/* Action Buttons: Save (saat mic mati), Saved File (Modal), New File */}
      <div className="flow-actions-group">
        {/* Tombol Save cepat saat mic mati */}
        {!isRecording && onManualSave && (
          <button
            type="button"
            onClick={onManualSave}
            disabled={!hasData || isSaving}
            className="flow-btn-manual-save"
            title="Simpan sesi aktif ke arsip dokumen (Save File)"
          >
            <Save size={13} className="text-emerald-300" />
            <span>{isSaving ? "Menyimpan..." : "Save"}</span>
          </button>
        )}

        {/* Saved File Button (View, Edit, Delete modal) */}
        <button
          type="button"
          onClick={onOpenSavedFiles}
          className="flow-btn-saved"
          title="Buka Daftar Dokumen Terarsip (Saved File) - View, Edit, Delete"
        >
          <FolderOpen size={14} className="text-amber-400" />
          <span className="font-semibold">Saved File</span>
          {savedCount > 0 && (
            <span className="flow-count-badge">{savedCount}</span>
          )}
        </button>

        {/* New File Button (loops back to On Mic) */}
        <button
          type="button"
          onClick={onNewFile}
          className="flow-btn-new"
          title="Mulai Sesi Baru & Reload Bersih (New File -> On Mic)"
        >
          <PlusCircle size={14} className="text-blue-400" />
          <span className="font-semibold">New File</span>
          <span className="text-[10px] text-zinc-400 ml-1">↺ On Mic</span>
        </button>
      </div>
    </div>
  );
};
