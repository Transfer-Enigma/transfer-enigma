import {
    createCachePolicy,
    deleteCachePolicy,
    invalidateCachePolicies,
    listCachePolicies,
    updateCachePolicy,
} from "@/api/CachePolicies";
import type { ICachePolicy, ICachePolicyPatch } from "@/interfaces/CachePolicy";
import { CACHE_ENTITIES } from "@/interfaces/CachePolicy";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const emptyForm = {
    id: null as number | null,
    source: "",
    entity: "rates",
    enabled: true,
    ttl: 3600,
};

export default function CachePolicies() {
    const [ policies, setPolicies ] = useState<ICachePolicy[]>([]);
    const [ form, setForm ] = useState(emptyForm);
    const [ loading, setLoading ] = useState(false);
    const [ saving, setSaving ] = useState<Set<number>>(new Set());
    const [ deleting, setDeleting ] = useState<Set<number>>(new Set());
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
    };

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setMessage(null);
        setError(null);

        const payload = {
            source: form.source.trim(),
            entity: form.entity.trim(),
            enabled: form.enabled,
            ttl: form.ttl,
        };

        if (!payload.source || !payload.entity) {
            setError("Source и Entity обязательны");
            return;
        }
        if (payload.ttl <= 0) {
            setError("TTL должен быть больше нуля");
            return;
        }

        try {
            await createCachePolicy(payload);
            setMessage("Политика кэша создана");
            resetForm();
            await loadPolicies();
        } catch (e) {
            setError((e as Error).message || "Ошибка создания");
        }
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
        field: "enabled" | "ttl",
        value: boolean | number,
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
            if (draft.entity !== policy.entity) patch.entity = draft.entity;
            if (draft.enabled !== policy.enabled) patch.enabled = draft.enabled;
            if (draft.ttl !== policy.ttl) patch.ttl = draft.ttl;
            if (Object.keys(patch).length === 0) {
                setSaving((prev) => {
                    const next = new Set(prev);
                    next.delete(policy.id);
                    return next;
                });
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

    const handleDelete = async (policy: ICachePolicy) => {
        if (!window.confirm(`Удалить политику кэша ${policy.source}.${policy.entity}?`))
            return;
        setError(null);
        setDeleting((prev) => {
            const next = new Set(prev);
            next.add(policy.id);
            return next;
        });
        try {
            await deleteCachePolicy(policy.id);
            setMessage("Политика кэша удалена");
            await loadPolicies();
        } catch (e) {
            setError((e as Error).message || "Ошибка удаления");
        } finally {
            setDeleting((prev) => {
                const next = new Set(prev);
                next.delete(policy.id);
                return next;
            });
        }
    };

    const handleInvalidateSource = async (policy: ICachePolicy) => {
        setError(null);
        try {
            await invalidateCachePolicies(policy.source);
            setMessage(`Кэш источника ${policy.source} инвалидирован`);
        } catch (e) {
            setError((e as Error).message || "Ошибка инвалидации");
        }
    };

    const handleInvalidateAll = async () => {
        setError(null);
        try {
            await invalidateCachePolicies();
            setMessage("Весь кэш инвалидирован");
            await loadPolicies();
        } catch (e) {
            setError((e as Error).message || "Ошибка инвалидации");
        }
    };

    const handleSearch = (event: ChangeEvent<HTMLInputElement>) => {
        setSourceFilter(event.target.value);
    };

    const filtered = policies.filter(
        (p) => !sourceFilter || p.source.toLowerCase().includes(sourceFilter.toLowerCase()),
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
                <button type="button" onClick={ handleInvalidateAll } disabled={ loading }>
                    Инвалидировать весь кэш
                </button>
                <input
                    placeholder="Фильтр по source"
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
                        const isDeleting = deleting.has(policy.id);
                        const isEditingThis = isEditing && editingPolicy?.id === policy.id;
                        return (
                            <tr key={ policy.id }>
                                <td>{ policy.id }</td>
                                <td>{ policy.source }</td>
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
                                        onClick={ () => void handleInvalidateSource(policy) }
                                        disabled={ isSaving || isDeleting || loading }
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
                                                disabled={ isSaving || isDeleting }
                                            >
                                                Отмена
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                type="button"
                                                onClick={ () => void handleEdit(policy) }
                                                disabled={ isSaving || isDeleting }
                                            >
                                                Изменить
                                            </button>
                                            <button
                                                type="button"
                                                onClick={ () => void handleDelete(policy) }
                                                disabled={ isDeleting || isSaving }
                                            >
                                                Удалить
                                            </button>
                                        </>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            <form onSubmit={ handleSubmit } className="button-group" style={ { marginTop: "1rem" } }>
                <label>
                    Source
                    <input
                        value={ form.source }
                        onChange={ (e) => setForm({ ...form, source: e.target.value }) }
                        placeholder="cbr"
                        disabled={ isEditing }
                    />
                </label>
                <label>
                    Entity
                    <select
                        value={ form.entity }
                        onChange={ (e) => setForm({ ...form, entity: e.target.value }) }
                        disabled={ isEditing }
                    >
                        { CACHE_ENTITIES.map((e) => (
                            <option key={ e.value } value={ e.value }>
                                { e.label }
                            </option>
                        )) }
                    </select>
                </label>
                <label>
                    Enabled
                    <select
                        value={ String(form.enabled) }
                        onChange={ (e) => setForm({ ...form, enabled: e.target.value === "true" }) }
                        disabled={ isEditing }
                    >
                        <option value="true">Да</option>
                        <option value="false">Нет</option>
                    </select>
                </label>
                <label>
                    TTL (сек)
                    <input
                        type="number"
                        step="1"
                        min="1"
                        value={ form.ttl }
                        onChange={ (e) =>
                            setForm({ ...form, ttl: Number(e.target.value) || 3600 })
                        }
                        disabled={ isEditing }
                    />
                </label>
                <button type="submit" disabled={ loading }>
                    { isEditing ? "Сохранить" : "Добавить" }
                </button>
                { isEditing && (
                    <button type="button" onClick={ resetForm } disabled={ loading }>
                        Отмена
                    </button>
                ) }
            </form>
        </div>
    );
}
