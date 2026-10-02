import { ChangeEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { deleteAllData, syncDocument, updateFromFile, updateFromGsheets, uploadBackup, validateDocument } from "@/api/Data";
import { deleteSyncDocument, listSyncDocuments } from "@/api/SyncDocuments";
import { API_ENDPOINTS } from "@/api/ApiConfig";
import { SyncDocument, SyncErrorItem, UpdateResponse, ValidateResponse } from "@/interfaces/Data";

function formatApiError(e: unknown, fallback: string): string {
    if (axios.isAxiosError(e)) {
        const status = e.response?.status;
        const data = e.response?.data;
        if (status !== undefined && data !== undefined)
            return `Ошибка ${status}: ${JSON.stringify(data)}`;
        if (status !== undefined)
            return `Ошибка ${status}: ${(e as Error).message}`;
    }
    return (e as Error).message || fallback;
}

export default function DataImport() {
    const [ loading, setLoading ] = useState(false);
    const [ message, setMessage ] = useState<string | null>(null);
    const [ error, setError ] = useState<string | null>(null);
    const [ warnings, setWarnings ] = useState<any[]>([]);
    const [ showWarnings, setShowWarnings ] = useState(false);
    const backupFileInputRef = useRef<HTMLInputElement | null>(null);
    const dataFileInputRef = useRef<HTMLInputElement | null>(null);

    const handleOperation = async (operation: () => Promise<void | UpdateResponse>, successText: string) => {
        setLoading(true);
        setMessage(null);
        setError(null);
        setWarnings([]);
        setShowWarnings(false);

        try {
            const result = await operation();
            setMessage(successText);
            if (result && "warnings" in result)
                setWarnings(result.warnings);
        } catch (e) {
            setError(formatApiError(e, "Произошла ошибка"));
        } finally {
            setLoading(false);
        }
    };

    const [ documents, setDocuments ] = useState<SyncDocument[]>([]);
    const [ selection, setSelection ] = useState<Record<number, string[]>>({});
    const [ expanded, setExpanded ] = useState<Record<number, boolean>>({});
    const [ runMode, setRunMode ] = useState<"validate" | "sync">("validate");
    const [ loadOnWarnings, setLoadOnWarnings ] = useState(true);
    const [ syncMode, setSyncMode ] = useState<"all" | "new">("all");
    const [ fixChecked, setFixChecked ] = useState(false);
    const [ highlightChecked, setHighlightChecked ] = useState(false);
    const [ ensureUids, setEnsureUids ] = useState(false);
    const [ running, setRunning ] = useState(false);
    const [ runResults, setRunResults ] = useState<any[]>([]);

    const SHEET_ROLES = [
        { key: "sea", label: "Море", field: "sea_ws" },
        { key: "rail", label: "ЖД", field: "rail_ws" },
        { key: "truck", label: "АВТО", field: "truck_ws" },
        { key: "dropp", label: "ДРОПП", field: "dropp_ws" },
        { key: "points", label: "Точки", field: "points_ws" },
        { key: "services", label: "Услуги", field: "services_ws" },
    ] as const;

    const docSheets = (doc: SyncDocument) =>
        SHEET_ROLES.filter((role) => (doc as any)[role.field]);

    const loadDocuments = async () => {
        try {
            setDocuments(await listSyncDocuments());
        } catch (e) {
            setError(formatApiError(e, "Не удалось загрузить документы"));
        }
    };

    useEffect(() => {
        void loadDocuments();
    }, []);

    const toggleDocument = (doc: SyncDocument) => {
        setSelection((prev) => {
            const next = { ...prev };
            if (next[doc.id])
                delete next[doc.id];
            else
                next[doc.id] = docSheets(doc).map((role) => role.key);
            return next;
        });
    };

    const toggleSheet = (doc: SyncDocument, sheetKey: string) => {
        setSelection((prev) => {
            const current = prev[doc.id] ?? [];
            const next = { ...prev };
            if (current.includes(sheetKey)) {
                const rest = current.filter((key) => key !== sheetKey);
                if (rest.length === 0)
                    delete next[doc.id];
                else
                    next[doc.id] = rest;
            } else {
                next[doc.id] = [ ...current, sheetKey ];
            }
            return next;
        });
    };

    const handleDeleteDocument = async (doc: SyncDocument) => {
        if (!window.confirm(`Исключить документ "${doc.title}" из синхронизации? Запись будет удалена.`))
            return;
        try {
            await deleteSyncDocument(doc.id);
            setSelection((prev) => {
                const next = { ...prev };
                delete next[doc.id];
                return next;
            });
            await loadDocuments();
        } catch (e) {
            setError(formatApiError(e, "Не удалось удалить документ"));
        }
    };

    const handleRun = async () => {
        const selectedDocs = documents.filter((doc) => selection[doc.id]?.length > 0);
        if (selectedDocs.length === 0) {
            setError("Выберите хотя бы один документ");
            return;
        }
        setRunning(true);
        setError(null);
        const results: any[] = [];
        try {
            for (const doc of selectedDocs) {
                const mapped = docSheets(doc).map((role) => role.key);
                const selected = selection[doc.id];
                const params = {
                    document_id: doc.id,
                    sheets: selected.length < mapped.length ? selected : undefined,
                    load_on_warnings: loadOnWarnings,
                    mode: syncMode,
                    fix: fixChecked,
                    highlight: highlightChecked,
                    ensure_uids: ensureUids,
                };
                try {
                    if (runMode === "validate") {
                        const report: ValidateResponse = await validateDocument(params);
                        results.push({ doc, ok: true, report });
                    } else {
                        const result: UpdateResponse = await syncDocument(params);
                        results.push({ doc, ok: true, report: result });
                    }
                } catch (e) {
                    results.push({ doc, ok: false, error: formatApiError(e, "Ошибка запуска") });
                }
            }
            setRunResults(results);
            await loadDocuments();
        } finally {
            setRunning(false);
        }
    };

    const renderRunResult = (result: any, index: number) => {
        const findings: SyncErrorItem[] = [
            ...(result.report?.errors ?? []),
            ...(result.report?.warnings ?? []),
        ];
        return (
            <div key={ index } className="run-result">
                <div className="warning-header">
                    { result.doc.title } — { result.ok ? "OK" : `Ошибка: ${result.error}` }
                    { result.report?.checked_rows !== undefined && ` (проверено строк: ${result.report.checked_rows})` }
                    { result.report?.routesInsertedCount !== undefined && ` (маршрутов: ${result.report.routesInsertedCount})` }
                </div>
                { findings.length > 0 && (
                    <ul>
                        { findings.map((finding, findingIndex) => (
                            <li key={ findingIndex }>
                                { finding.message ?? finding.error ?? JSON.stringify(finding) }
                                { finding.code ? ` [${finding.code}]` : "" }
                                { finding.sheet ? `, лист: ${finding.sheet}` : "" }
                                { finding.row ? `, строка: ${finding.row}` : "" }
                                { finding.cell ? `, ячейка: ${finding.cell}` : "" }
                            </li>
                        )) }
                    </ul>
                ) }
            </div>
        );
    };

    const handleUpdateFromGsheets = async () => {
        await handleOperation(
            async () => updateFromGsheets(),
            "Обновление данных из Google Sheets выполнено.",
        );
    };

    const handleUpdateFromFile = () => dataFileInputRef.current?.click();

    const handleDeleteAllData = async () => {
        await handleOperation(
            async () => deleteAllData(),
            "Все данные успешно удалены.",
        );
    };

    const handleCreateBackup = () => window.open(API_ENDPOINTS.DATA.DB, "_blank");

    const handleUploadBackup = () => backupFileInputRef.current?.click();

    const handleBackupFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file)
            return;

        await handleOperation(
            async () => uploadBackup(file),
            "Резервная копия успешно загружена.",
        );

        event.target.value = "";
    };

    const handleDataFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file)
            return;

        await handleOperation(
            async () => updateFromFile(file),
            "Данные успешно обновлены.",
        );

        event.target.value = "";
    };

    const handleHardUpdate = async () => {
        setLoading(true);
        setMessage(null);
        setError(null);
        setWarnings([]);
        setShowWarnings(false);

        try {
            window.open(API_ENDPOINTS.DATA.DB, "_blank");
            await deleteAllData();
            const result = await updateFromGsheets();
            setMessage("Hard update выполнен: резервная копия создана, данные удалены, данные обновлены.");
            if (result && "warnings" in result)
                setWarnings(result.warnings);
        } catch (e) {
            setError(formatApiError(e, "Произошла ошибка при жестком обновлении."));
        } finally {
            setLoading(false);
        }
    };

    const renderWarning = (warning: any, index: number) => {
        if (warning.rows_list) {
            return (
                <div key={ index } className="warning-item">
                    <div className="warning-header">{ warning.error }</div>
                    <ul>
                        {warning.rows_list.map((row: any, rowIndex: number) => (
                            <li key={ rowIndex }>
                                { row.error }
                                <ul>
                                    { row.columns.map((col: string, colIndex: number) => (
                                        <li key={ colIndex }>{ col }</li>
                                    )) }
                                </ul>
                            </li>
                        ))}
                    </ul>
                </div>
            );
        } else if (warning.row_numbers) {
            return (
                <div key={ index } className="warning-item">
                    <div className="warning-header">{ warning.error }</div>
                    <div>Строки: { warning.row_numbers.join(", ") }</div>
                </div>
            );
        } else {
            return (
                <div key={ index } className="warning-item">
                    <div className="warning-header">{ warning.error ?? warning.message ?? String(warning) }</div>
                    { warning.code && (
                        <div>
                            Код: { warning.code }
                            { warning.sheet ? `, лист: ${warning.sheet}` : "" }
                            { warning.row ? `, строка: ${warning.row}` : "" }
                            { warning.cell ? `, ячейка: ${warning.cell}` : "" }
                        </div>
                    ) }
                </div>
            );
        }
    };

    return (
        <div className="data-import-page">
            <h1>Загрузка данных</h1>

            <div className="sync-panel">
                <h2>Синхронизация документов</h2>

                { documents.length === 0 && <div>Нет документов. Добавьте Google Doc или файл.</div> }

                { documents.map((doc) => {
                    const mapped = docSheets(doc);
                    const selected = selection[doc.id] ?? [];
                    const allSelected = selected.length > 0 && selected.length === mapped.length;
                    return (
                        <div key={ doc.id } className="sync-document">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={ allSelected }
                                    onChange={ () => toggleDocument(doc) }
                                    disabled={ running }
                                />
                                { ` ${doc.title} (${doc.source_type})` }
                            </label>
                            { doc.last_status && <span>{ ` [${doc.last_status}]` }</span> }
                            <button type="button" onClick={ () => handleDeleteDocument(doc) } disabled={ running }>
                                🗑
                            </button>
                            <button
                                type="button"
                                onClick={ () => setExpanded((prev) => ({ ...prev, [doc.id]: !prev[doc.id] })) }
                                disabled={ running }
                            >
                                { expanded[doc.id] ? "▲" : "▼" }
                            </button>
                            { expanded[doc.id] && (
                                <ul>
                                    { mapped.map((role) => (
                                        <li key={ role.key }>
                                            <label>
                                                <input
                                                    type="checkbox"
                                                    checked={ selected.includes(role.key) }
                                                    onChange={ () => toggleSheet(doc, role.key) }
                                                    disabled={ running }
                                                />
                                                { ` ${role.label}: ${(doc as any)[role.field]}` }
                                            </label>
                                        </li>
                                    )) }
                                </ul>
                            ) }
                        </div>
                    );
                }) }

                <div className="run-options">
                    <label>
                        <input
                            type="checkbox"
                            checked={ runMode === "sync" }
                            onChange={ (event) => setRunMode(event.target.checked ? "sync" : "validate") }
                            disabled={ running }
                        />
                        { " Синхронизировать (иначе — только проверить)" }
                    </label>
                    <label>
                        <input
                            type="checkbox"
                            checked={ loadOnWarnings }
                            onChange={ (event) => setLoadOnWarnings(event.target.checked) }
                            disabled={ running }
                        />
                        { " Загружать при предупреждениях" }
                    </label>
                    <label>
                        { " Режим: " }
                        <select value={ syncMode } onChange={ (event) => setSyncMode(event.target.value as "all" | "new") } disabled={ running }>
                            <option value="all">все (upsert)</option>
                            <option value="new">только новые</option>
                        </select>
                    </label>
                    <label>
                        <input
                            type="checkbox"
                            checked={ fixChecked }
                            onChange={ (event) => setFixChecked(event.target.checked) }
                            disabled={ running }
                        />
                        { " Исправить ошибки" }
                    </label>
                    <label>
                        <input
                            type="checkbox"
                            checked={ highlightChecked }
                            onChange={ (event) => setHighlightChecked(event.target.checked) }
                            disabled={ running }
                        />
                        { " Подсветить невалидные поля" }
                    </label>
                    <label>
                        <input
                            type="checkbox"
                            checked={ ensureUids }
                            onChange={ (event) => setEnsureUids(event.target.checked) }
                            disabled={ running }
                        />
                        { " Проставить UID" }
                    </label>
                </div>

                <button type="button" onClick={ handleRun } disabled={ running }>
                    { running ? "Выполняется..." : "Запустить" }
                </button>

                { runResults.length > 0 && (
                    <div className="run-results">
                        { runResults.map((result, index) => renderRunResult(result, index)) }
                    </div>
                ) }
            </div>

            <div className="button-group">
                <button type="button" onClick={ handleUpdateFromGsheets } disabled={ loading }>
                    Обновить из Google Sheets
                </button>
                <button type="button" onClick={ handleUpdateFromFile } disabled={ loading }>
                    Обновить из XLSX файла
                </button>
                <button type="button" onClick={ handleDeleteAllData } disabled={ loading }>
                    Удалить все данные
                </button>
                <button type="button" onClick={ handleCreateBackup } disabled={ loading }>
                    Создать резервную копию
                </button>
                <button type="button" onClick={ handleUploadBackup } disabled={ loading }>
                    Загрузить резервную копию
                </button>
                <button type="button" onClick={ handleHardUpdate } disabled={ loading }>
                    Hard update
                </button>
            </div>

            { message && <div className="message success">{ message }</div> }
            { error && <div className="message error">{ error }</div> }

            { warnings.length > 0 && (
                <div className="warnings-section">
                    <button
                        type="button"
                        onClick={ () => setShowWarnings(!showWarnings) }
                        className="toggle-warnings"
                    >
                        { showWarnings ? "Скрыть ошибки" : `Показать ошибки (${warnings.length})` }
                    </button>
                    { showWarnings && (
                        <div className="warnings-list">
                            { warnings.map((warning, index) => renderWarning(warning, index)) }
                        </div>
                    ) }
                </div>
            ) }

            <input
                ref={ backupFileInputRef }
                type="file"
                style={ { display: "none" } }
                onChange={ handleBackupFileSelected }
                accept="*/*"
            />
            <input
                ref={ dataFileInputRef }
                type="file"
                style={ { display: "none" } }
                onChange={ handleDataFileSelected }
                accept="*/*"
            />
        </div>
    );
}
