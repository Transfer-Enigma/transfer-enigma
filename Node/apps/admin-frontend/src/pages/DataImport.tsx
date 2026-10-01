import { ChangeEvent, useRef, useState } from "react";
import axios from "axios";
import { deleteAllData, updateFromFile, updateFromGsheets, uploadBackup } from "@/api/Data";
import { API_ENDPOINTS } from "@/api/ApiConfig";
import { UpdateResponse } from "@/interfaces/Data";

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
