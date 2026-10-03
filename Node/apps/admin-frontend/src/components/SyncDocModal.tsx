import { useEffect, useState } from "react";
import { createSyncDocument, patchSyncDocument, SheetsPreview } from "@/api/SyncDocuments";

export interface ModalSource {
    kind: "google" | "file";
    url: string;
    fileName: string;
    docId?: number;
    preview: SheetsPreview;
}

interface ModalProps {
    source: ModalSource | null;
    onClose: () => void;
    onSaved: () => void;
}

const ROLE_COLUMNS = [
    { column: "sea_ws", label: "Море" },
    { column: "rail_ws", label: "ЖД" },
    { column: "truck_ws", label: "АВТО" },
    { column: "dropp_ws", label: "ДРОПП" },
    { column: "points_ws", label: "Точки" },
    { column: "services_ws", label: "Услуги" },
];

export default function SyncDocModal({ source, onClose, onSaved }: ModalProps) {
    const [ title, setTitle ] = useState("");
    const [ mapping, setMapping ] = useState<Record<string, string>>({});
    const [ singleRole, setSingleRole ] = useState("");
    const [ saving, setSaving ] = useState(false);
    const [ modalError, setModalError ] = useState<string | null>(null);

    useEffect(() => {
        if (!source)
            return;
        setTitle(source.kind === "google" ? source.url : source.fileName);
        const initial: Record<string, string> = {};
        for (const sheet of source.preview.sheets)
            initial[sheet] = source.preview.suggested_mapping[sheet] ?? "";
        setMapping(initial);
        setSingleRole("");
        setModalError(null);
    }, [ source ]);

    if (!source)
        return null;

    const handleSave = async () => {
        setSaving(true);
        setModalError(null);
        try {
            if (source.preview.single_sheet) {
                const payload: Record<string, unknown> = { title };
                for (const role of ROLE_COLUMNS)
                    payload[role.column] = role.column === singleRole ? "sheet" : null;
                if (source.kind === "google" && source.docId !== undefined)
                    await patchSyncDocument(source.docId, payload);
                else
                    await createSyncDocument({ ...payload, url: source.url, source_type: "file", file_name: source.fileName });
            } else {
                const payload: Record<string, unknown> = { title };
                for (const role of ROLE_COLUMNS) {
                    const sheet = Object.keys(mapping).find((name) => mapping[name] === role.column) ?? null;
                    payload[role.column] = sheet;
                }
                if (source.kind === "google" && source.docId !== undefined)
                    await patchSyncDocument(source.docId, payload);
                else
                    await createSyncDocument({ ...payload, url: source.url, source_type: "file", file_name: source.fileName });
            }
            onSaved();
            onClose();
        } catch (e) {
            setModalError((e as Error).message || "Не удалось сохранить документ");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div
            style={ {
                position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
                background: "rgba(0,0,0,0.5)", display: "flex",
                alignItems: "center", justifyContent: "center", zIndex: 1000,
            } }
            onClick={ onClose }
        >
            <div
                style={ { background: "white", padding: 20, minWidth: 400, maxHeight: "80vh", overflow: "auto" } }
                onClick={ (event) => event.stopPropagation() }
            >
                <h3>Настройка документа</h3>
                <label>
                    { "Название: " }
                    <input value={ title } onChange={ (event) => setTitle(event.target.value) } disabled={ saving } />
                </label>
                { source.preview.single_sheet ? (
                    <div>
                        <p>Файл с одним листом — выберите его роль:</p>
                        <select value={ singleRole } onChange={ (event) => setSingleRole(event.target.value) } disabled={ saving }>
                            <option value="">— не синхронизировать —</option>
                            { ROLE_COLUMNS.map((role) => (
                                <option key={ role.column } value={ role.column }>{ role.label }</option>
                            )) }
                        </select>
                    </div>
                ) : (
                    <ul>
                        { source.preview.sheets.map((sheet) => (
                            <li key={ sheet }>
                                <label>
                                    <input
                                        type="checkbox"
                                        checked={ (mapping[sheet] ?? "") !== "" }
                                        onChange={ (event) => setMapping((prev) => ({
                                            ...prev,
                                            [sheet]: event.target.checked
                                                ? (source.preview.suggested_mapping[sheet] ?? "")
                                                : "",
                                        })) }
                                        disabled={ saving }
                                    />
                                    { ` ${sheet} → ` }
                                </label>
                                <select
                                    value={ mapping[sheet] ?? "" }
                                    onChange={ (event) => setMapping((prev) => ({ ...prev, [sheet]: event.target.value })) }
                                    disabled={ saving }
                                >
                                    <option value="">— исключить —</option>
                                    { ROLE_COLUMNS.map((role) => (
                                        <option key={ role.column } value={ role.column }>{ role.label }</option>
                                    )) }
                                </select>
                            </li>
                        )) }
                    </ul>
                ) }
                { modalError && <div className="message error">{ modalError }</div> }
                <button type="button" onClick={ handleSave } disabled={ saving }>
                    { saving ? "Сохранение..." : "Сохранить" }
                </button>
                <button type="button" onClick={ onClose } disabled={ saving }>
                    Отмена
                </button>
            </div>
        </div>
    );
}
