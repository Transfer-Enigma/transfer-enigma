import { createRate, deleteRate, listRates, updateRate } from "@/api/Rates";
import type { IRate } from "@/interfaces/Rate";
import { FormEvent, useEffect, useState } from "react";

const emptyForm = { code: "", rate: "", date: "" };

export default function RatesManagement() {
    const [ rates, setRates ] = useState<IRate[]>([]);
    const [ form, setForm ] = useState(emptyForm);
    const [ editingId, setEditingId ] = useState<number | null>(null);
    const [ loading, setLoading ] = useState(false);
    const [ message, setMessage ] = useState<string | null>(null);
    const [ error, setError ] = useState<string | null>(null);

    const loadRates = async () => {
        setLoading(true);
        setError(null);
        try {
            setRates(await listRates());
        } catch (e) {
            setError((e as Error).message || "Не удалось загрузить курсы валют");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadRates();
    }, []);

    const resetForm = () => {
        setForm(emptyForm);
        setEditingId(null);
    };

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setMessage(null);
        setError(null);

        const payload = {
            code: form.code.trim().toUpperCase(),
            rate: Number(form.rate),
            date: form.date,
        };

        if (!payload.code || payload.code.length !== 3) {
            setError("Код валюты должен быть длиной 3 символа (например, USD)");
            return;
        }
        if (!payload.rate || payload.rate <= 0) {
            setError("Курс должен быть положительным числом");
            return;
        }
        if (!payload.date) {
            setError("Дата обязательна");
            return;
        }

        try {
            if (editingId)
                await updateRate(editingId, payload);
            else
                await createRate(payload);

            setMessage(editingId ? "Курс обновлён" : "Курс добавлен");
            resetForm();
            await loadRates();
        } catch (e) {
            setError((e as Error).message || "Ошибка сохранения");
        }
    };

    const handleEdit = (rate: IRate) => {
        setEditingId(rate.id);
        setForm({
            code: rate.code,
            rate: String(rate.rate),
            date: rate.date,
        });
    };

    const handleDelete = async (rate: IRate) => {
        if (!window.confirm(`Удалить курс ${rate.code} от ${rate.date}?`))
            return;

        setMessage(null);
        setError(null);
        try {
            await deleteRate(rate.id);
            if (editingId === rate.id)
                resetForm();
            setMessage("Курс удалён");
            await loadRates();
        } catch (e) {
            setError((e as Error).message || "Ошибка удаления");
        }
    };

    return (
        <div className="data-import-page">
            <h1>Курсы валют</h1>
            <p>Управление курсами валют относительно RUB. Автоматически обновляются ежедневно в 06:00 из CBR.</p>

            {loading && <p>Загрузка…</p>}
            {message && <div className="message success">{message}</div>}
            {error && <div className="message error">{error}</div>}

            <form onSubmit={ handleSubmit } className="button-group">
                <label>
                    Код валюты
                    <input
                        value={ form.code }
                        onChange={ e => setForm({ ...form, code: e.target.value }) }
                        placeholder="USD"
                        maxLength={ 3 }
                        style={ { textTransform: "uppercase" } }
                    />
                </label>
                <label>
                    Курс к RUB
                    <input
                        type="number"
                        min="0"
                        step="0.000001"
                        value={ form.rate }
                        onChange={ e => setForm({ ...form, rate: e.target.value }) }
                    />
                </label>
                <label>
                    Дата
                    <input
                        type="date"
                        value={ form.date }
                        onChange={ e => setForm({ ...form, date: e.target.value }) }
                    />
                </label>
                <button type="submit">{ editingId ? "Сохранить" : "Добавить" }</button>
                {editingId && <button type="button" onClick={ resetForm }>Отмена</button>}
            </form>

            <table>
                <thead>
                    <tr>
                        <th>Код</th>
                        <th>Курс</th>
                        <th>Дата</th>
                        <th>Создан</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {rates.map(rate => (
                        <tr key={ rate.id }>
                            <td>{ rate.code }</td>
                            <td>{ rate.rate }</td>
                            <td>{ rate.date }</td>
                            <td>{ rate.created_at }</td>
                            <td>
                                <button type="button" onClick={ () => handleEdit(rate) }>Изменить</button>
                                <button type="button" onClick={ () => void handleDelete(rate) }>Удалить</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
