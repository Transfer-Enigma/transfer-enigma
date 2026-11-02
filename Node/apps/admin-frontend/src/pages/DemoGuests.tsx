import { createDemoGuest, deleteDemoGuest, listDemoGuests, updateDemoGuest } from "@/api/DemoGuests";
import type { IDemoGuest } from "@/interfaces/DemoGuest";
import { FormEvent, useEffect, useState } from "react";

const MAIN_CURRENCIES = [ "USD", "EUR", "RUB", "CNY" ];
const emptyForm = { uid: "", sea_profit: "0", sea_profit_currency: "USD", rail_profit: "0", rail_profit_currency: "USD" };

export default function DemoGuests() {
    const [ guests, setGuests ] = useState<IDemoGuest[]>([]);
    const [ currencies, setCurrencies ] = useState<string[]>(MAIN_CURRENCIES);
    const [ form, setForm ] = useState(emptyForm);
    const [ editingId, setEditingId ] = useState<number | null>(null);
    const [ loading, setLoading ] = useState(false);
    const [ message, setMessage ] = useState<string | null>(null);
    const [ error, setError ] = useState<string | null>(null);

    useEffect(() => {
        fetch("/api/v2/rates")
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                const rates = data && typeof data === "object"
                    ? (data as { rates?: Record<string, unknown> }).rates
                    : null;
                if (rates && typeof rates === "object") {
                    const all = Object.keys(rates);
                    const main = MAIN_CURRENCIES.filter(c => all.includes(c));
                    const rest = all.filter(c => !main.includes(c));
                    setCurrencies([ ...main, ...rest ]);
                }
            })
            .catch(() => {});
    }, []);

    const loadGuests = async () => {
        setLoading(true);
        setError(null);
        try {
            setGuests(await listDemoGuests());
        } catch (e) {
            setError((e as Error).message || "Не удалось загрузить демо-пользователей");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadGuests();
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
            uid: form.uid.trim(),
            sea_profit: Number(form.sea_profit),
            sea_profit_currency: form.sea_profit_currency,
            rail_profit: Number(form.rail_profit),
            rail_profit_currency: form.rail_profit_currency,
        };

        if (!payload.uid) {
            setError("UID обязателен");
            return;
        }

        try {
            if (editingId)
                await updateDemoGuest(editingId, payload);
            else
                await createDemoGuest(payload);

            setMessage(editingId ? "Демо-пользователь обновлён" : "Демо-пользователь создан");
            resetForm();
            await loadGuests();
        } catch (e) {
            setError((e as Error).message || "Ошибка сохранения");
        }
    };

    const generateUid = () => {
        const random = Math.random().toString(36).substring(2, 10);
        setForm({ ...form, uid: random });
    };

    const handleEdit = (guest: IDemoGuest) => {
        setEditingId(guest.id);
        setForm({
            uid: guest.uid,
            sea_profit: String(guest.sea_profit),
            sea_profit_currency: guest.sea_profit_currency,
            rail_profit: String(guest.rail_profit),
            rail_profit_currency: guest.rail_profit_currency,
        });
    };

    const handleDelete = async (guest: IDemoGuest) => {
        if (!window.confirm(`Удалить демо-пользователя ${guest.uid}?`))
            return;

        setMessage(null);
        setError(null);
        try {
            await deleteDemoGuest(guest.id);
            if (editingId === guest.id)
                resetForm();
            setMessage("Демо-пользователь удалён");
            await loadGuests();
        } catch (e) {
            setError((e as Error).message || "Ошибка удаления");
        }
    };

    return (
        <div className="data-import-page">
            <h1>Демо-ссылки</h1>
            <p>UID используется в ссылке вида <code>/demo/&lt;UID&gt;</code> на пользовательском сайте.</p>

            {loading && <p>Загрузка…</p>}
            {message && <div className="message success">{message}</div>}
            {error && <div className="message error">{error}</div>}

            <form onSubmit={ handleSubmit } className="button-group">
                <label>
                    UID
                    <input
                        value={ form.uid }
                        onChange={ e => setForm({ ...form, uid: e.target.value }) }
                        placeholder="partner-2026"
                    />
                    <button type="button" onClick={ generateUid } style={ { marginTop: "0.3rem", padding: "0.3rem 0.6rem", fontSize: "0.85rem", background: "#6c757d", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" } }>Сгенерировать UID</button>
                </label>
                <label>
                    Sea profit
                    <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={ form.sea_profit }
                        onChange={ e => setForm({ ...form, sea_profit: e.target.value }) }
                    />
                    <select
                        value={ form.sea_profit_currency }
                        onChange={ e => setForm({ ...form, sea_profit_currency: e.target.value }) }
                    >
                        { currencies.map(c => <option key={ c } value={ c }>{ c }</option>) }
                    </select>
                </label>
                <label>
                    Rail profit
                    <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={ form.rail_profit }
                        onChange={ e => setForm({ ...form, rail_profit: e.target.value }) }
                    />
                    <select
                        value={ form.rail_profit_currency }
                        onChange={ e => setForm({ ...form, rail_profit_currency: e.target.value }) }
                    >
                        { currencies.map(c => <option key={ c } value={ c }>{ c }</option>) }
                    </select>
                </label>
                <button type="submit">{ editingId ? "Сохранить" : "Добавить" }</button>
                {editingId && <button type="button" onClick={ resetForm }>Отмена</button>}
            </form>

            <table>
                <thead>
                    <tr>
                        <th>UID</th>
                        <th>Sea profit</th>
                        <th>Rail profit</th>
                        <th>Демо-ссылка</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {guests.map(guest => (
                        <tr key={ guest.id }>
                            <td>{ guest.uid }</td>
                            <td>{ guest.sea_profit } { guest.sea_profit_currency }</td>
                            <td>{ guest.rail_profit } { guest.rail_profit_currency }</td>
                            <td><code>/demo/{ guest.uid }</code></td>
                            <td>
                                <button type="button" onClick={ () => handleEdit(guest) }>Изменить</button>
                                <button type="button" onClick={ () => void handleDelete(guest) }>Удалить</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
