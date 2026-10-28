import {
    invalidateAllCachePolicies,
    invalidateCachePolicy,
    listCachePolicies,
    updateCachePolicy,
} from "@/api/CachePolicies";
import type { ICachePolicy, ICachePolicyPatch } from "@/interfaces/CachePolicy";
import { ChangeEvent, useEffect, useState } from "react";

const emptyForm = {
    id: null as number | null,
    source: null as string | null,
    entity: "rates",
    enabled: true,
    ttl: 3600,
};

export default function CachePolicies() {
    const [ policies, setPolicies ] = useState<ICachePolicy[]>([]);
    const [ form, setForm ] = useState(emptyForm);
    const [ loading, setLoading ] = useState(false);
    const [ saving, setSaving ] = useState<Set<number>>(new Set());
    const [ invalidating, setInvalidating ] = useState<Set<number>>(new Set());
    const [ message, setMessage ] = useState<string | null>(null);
    const [ error, setError ] = useState<string | null>(null);
    const [ sourceFilter, setSourceFilter ] = useState("");

    const loadPolicies = async () => {
        setLoading(true);
        setError(null);
        try {
            setPolicies(await listCachePolicies(sourceFilter || undefined));
        } catch (e) {
            setError((e as Error).message || "Не удалось загрузить политики кэша");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadPolicies();
    }, [ sourceFilter ]);

    const resetForm = () => {
        setForm(emptyForm);
        setSaving((prev) => {
            const next = new Set(prev);
            next.delete(form.id);
            return next;
        });
    };

    const handleEdit = (policy: ICachePolicy) => {
        setForm({
            id: policy.id,
            source: policy.source,
            entity: policy.entity,
            enabled: policy.enabled,
            ttl: policy.ttl,
        });
        setSaving((prev) => {
            const next = new Set(prev);
            next.add(policy.id);
            return next;
        });
    };

    const handleEditChange = (
        policy: ICachePolicy,
        field: "source" | "entity" | "enabled" | "ttl",
        value: string | boolean | number,
    ) => {
        setError(null);
        setMessage(null);
        setForm((prev) => {
            if (prev.id === policy.id) {
                return { ...prev, [field]: value };
            }
            return prev;
        });
        setSaving((prev) => {
            const next = new Set(prev);
            next.add(policy.id);
            return next;
        });
    };

    const handleSave = async (policy: ICachePolicy) => {
        const draft = form.id === policy.id ? form : null;
        if (!draft) return;
        setError(null);
        try {
            const patch: ICachePolicyPatch = {};
            if (draft.enabled !== policy.enabled) patch.enabled = draft.enabled;
            if (draft.ttl !== policy.ttl) patch.ttl = draft.ttl;
            if (Object.keys(patch).length === 0) {
                resetForm();
                return;
            }
            await updateCachePolicy(policy.id, patch);
            setSaving((prev) => {
                const next = new Set(prev);
                next.delete(policy.id);
                return next;
            });
            setMessage("Политика кэша обновлена");
            resetForm();
            await loadPolicies();
        } catch (e) {
            setError((e as Error).message || "Ошибка обновления");
            setSaving((prev) => {
                const next = new Set(prev);
                next.delete(policy.id);
                return next;
            });
        }
    };

    const handleInvalidatePolicy = async (policy: ICachePolicy) => {
        const label = policy.source ? `${policy.source}.${policy.entity}` : policy.entity;
        if (!window.confirm(`Очистить кэш политики ${label}?`))
            return;
        setError(null);
        setInvalidating((prev) => {
            const next = new Set(prev);
            next.add(policy.id);
            return next;
        });
        try {
            const deleted = await invalidateCachePolicy(policy.id);
            setMessage(`Кэш политики ${label} очищен (${deleted} ключей)`);
        } catch (e) {
            setError((e as Error).message || "Ошибка инвалидации");
        } finally {
            setInvalidating((prev) => {
                const next = new Set(prev);
                next.delete(policy.id);
                return next;
            });
        }
    };

    const handleInvalidateAll = async () => {
        if (!window.confirm("Очистить кэш всех политик?"))
            return;
        setError(null);
        try {
            const deleted = await invalidateAllCachePolicies();
            setMessage(`Весь кэш очищен (${deleted} ключей)`);
        } catch (e) {
            setError((e as Error).message || "Ошибка инвалидации");
        }
    };

    const handleSearch = (event: ChangeEvent<HTMLInputElement>) => {
        setSourceFilter(event.target.value);
    };

    const filtered = policies.filter(
        (p) =>
            !sourceFilter ||
            (p.source ?? "").toLowerCase().includes(sourceFilter.toLowerCase()) ||
            p.entity.toLowerCase().includes(sourceFilter.toLowerCase()),
    );
    const isEditing = form.id != null;
    const editingPolicy = isEditing ? filtered.find((p) => p.id === form.id) : null;

    return (
        <div className="cache-page">
            <h1>Кэш</h1>

            {loading && <p>Загрузка…</p>}
            {message && <div className="message success">{message}</div>}
            {error && <div className="message error">{error}</div>}

            <div className="button-group" style={ { marginBottom: "1rem", gap: "0.5rem" } }>
                <button type="button" onClick={ () => void handleInvalidateAll() } disabled={ loading }>
                    Инвалидировать весь кэш
                </button>
                <input
                    placeholder="Фильтр по source или entity"
                    value={ sourceFilter }
                    onChange={ handleSearch }
                />
            </div>

            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Source</th>
                        <th>Entity</th>
                        <th>Enabled</th>
                        <th>TTL (сек)</th>
                        <th>Инвалидация</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {filtered.map((policy) => {
                        const isSaving = saving.has(policy.id);
                        const isInvalidating = invalidating.has(policy.id);
                        const isEditingThis = isEditing && editingPolicy?.id === policy.id;
                        return (
                            <tr key={ policy.id }>
                                <td>{ policy.id }</td>
                                <td>{ policy.source ?? "—" }</td>
                                <td>{ policy.entity }</td>
                                <td>
                                    {isEditingThis ? (
                                        <select
                                            value={ String(form.enabled) }
                                            onChange={ (e) =>
                                                handleEditChange(
                                                    policy,
                                                    "enabled",
                                                    e.target.value === "true",
                                                )
                                            }
                                        >
                                            <option value="true">Да</option>
                                            <option value="false">Нет</option>
                                        </select>
                                    ) : (
                                        policy.enabled ? "Да" : "Нет"
                                    )}
                                </td>
                                <td>
                                    {isEditingThis ? (
                                        <input
                                            type="number"
                                            step="1"
                                            min="1"
                                            value={ form.ttl }
                                            onChange={ (e) =>
                                                handleEditChange(
                                                    policy,
                                                    "ttl",
                                                    Number(e.target.value) || 1,
                                                )
                                            }
                                        />
                                    ) : (
                                        policy.ttl
                                    )}
                                </td>
                                <td>
                                    <button
                                        type="button"
                                        onClick={ () => void handleInvalidatePolicy(policy) }
                                        disabled={ isSaving || isInvalidating || loading }
                                    >
                                        Инвалидировать
                                    </button>
                                </td>
                                <td>
                                    {isEditingThis ? (
                                        <>
                                            <button
                                                type="button"
                                                onClick={ () => void handleSave(policy) }
                                                disabled={ isSaving }
                                            >
                                                Сохранить
                                            </button>
                                            <button
                                                type="button"
                                                onClick={ resetForm }
                                                disabled={ isSaving }
                                            >
                                                Отмена
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                type="button"
                                                onClick={ () => void handleEdit(policy) }
                                                disabled={ isSaving }
                                            >
                                                Изменить
                                            </button>
                                        </>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
