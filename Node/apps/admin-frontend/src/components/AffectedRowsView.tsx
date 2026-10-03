import { useState } from "react";
import { AffectedRow } from "@/interfaces/Data";

interface ViewProps {
    rows: AffectedRow[];
}

function formatValue(value: unknown): string {
    if (value === null || value === undefined || value === "")
        return "—";
    return String(value);
}

export default function AffectedRowsView({ rows }: ViewProps) {
    const scopes = [ ...new Set(rows.map((row) => row.scope)) ];
    const [ scope, setScope ] = useState<string>(scopes[0] ?? "");
    const [ showBefore, setShowBefore ] = useState(false);

    const scopeRows = rows.filter((row) => row.scope === scope);
    const fixedRows = scopeRows.filter((row) => row.fixed);
    const errorRows = scopeRows.filter((row) => row.errors.length > 0);
    const columns = [ ...new Set(scopeRows.flatMap((row) => Object.keys(row.values))) ];

    const cellValue = (row: AffectedRow, column: string): { text: string; fixed: boolean; error: boolean } => {
        const fix = row.fixes.find((item) => item.column === column);
        const hasError = row.errors.some(
            (error) => error.cell === column
                || (error.details as any)?.columns?.includes?.(column),
        );
        if (fix && fix.old !== fix.new)
            return { text: formatValue(showBefore ? fix.old : fix.new), fixed: !showBefore, error: false };
        return { text: formatValue((row.values as any)[column]), fixed: false, error: hasError };
    };

    const renderRow = (row: AffectedRow) => (
        <tr key={ `${row.scope}-${row.row}` }>
            <td>{ row.row }</td>
            { columns.map((column) => {
                const cell = cellValue(row, column);
                return (
                    <td
                        key={ column }
                        style={ cell.error
                            ? { background: "#f8d7da" }
                            : cell.fixed ? { background: "#d4edda" } : undefined }
                    >
                        { cell.text }
                    </td>
                );
            }) }
        </tr>
    );

    return (
        <div className="affected-rows">
            <div>
                { scopes.map((name) => (
                    <button
                        key={ name }
                        type="button"
                        onClick={ () => setScope(name) }
                        disabled={ scope === name }
                    >
                        { `${name} (${rows.filter((row) => row.scope === name).length})` }
                    </button>
                )) }
                <label>
                    <input
                        type="checkbox"
                        checked={ showBefore }
                        onChange={ (event) => setShowBefore(event.target.checked) }
                    />
                    { " Показать до исправления" }
                </label>
            </div>

            { fixedRows.length > 0 && (
                <div>
                    <div className="warning-header">{ `Исправлено (${fixedRows.length})` }</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Строка</th>
                                { columns.map((column) => <th key={ column }>{ column }</th>) }
                            </tr>
                        </thead>
                        <tbody>
                            { fixedRows.map(renderRow) }
                        </tbody>
                    </table>
                </div>
            ) }

            { errorRows.length > 0 && (
                <div>
                    <div className="warning-header">{ `Ошибки (${errorRows.length})` }</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Строка</th>
                                { columns.map((column) => <th key={ column }>{ column }</th>) }
                            </tr>
                        </thead>
                        <tbody>
                            { errorRows.map(renderRow) }
                        </tbody>
                    </table>
                    <ul>
                        { errorRows.flatMap((row) => row.errors).map((error, index) => (
                            <li key={ index }>
                                { error.message ?? error.error ?? JSON.stringify(error) }
                                { error.code ? ` [${error.code}]` : "" }
                            </li>
                        )) }
                    </ul>
                </div>
            ) }
        </div>
    );
}
