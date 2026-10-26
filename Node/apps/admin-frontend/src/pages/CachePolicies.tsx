import {
    createCachePolicy,
    deleteCachePolicy,
    invalidateAllCachePolicies,
    invalidateCachePolicy,
    listCachePolicies,
    updateCachePolicy,
} from "@/api/CachePolicies";
import type { ICachePolicy, ICachePolicyPatch } from "@/interfaces/CachePolicy";
import {
    CACHE_SOURCES,
    MULTI_SOURCE_ENTITIES,
    SINGLE_SOURCE_ENTITIES,
    requiresSource,
} from "@/interfaces/CachePolicy";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

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
    const [ deleting, setDeleting ] = useState<Set<number>>(new Set());
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

    const handleEntityChange = (value: string) => {
        setForm((prev) => ({
            ...prev,
            entity: value,
            source: requiresSource(value) ? prev.source ?? "" : null,
        }));
    };

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setMessage(null);
        setError(null);

        const payload = {
            source: form.source,
            entity: form.entity.trim(),
            enabled: form.enabled,
            ttl: form.ttl,
        };

        if (!payload.entity) {
            setError("Entity обязателен");
            return;
        }
        if (requiresSource(payload.entity) && !payload.source) {
            setError("Source обязателен для этой сущности");
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

    const handleDelete = async (policy: ICachePolicy) => {
        const label = policy.source ? `${policy.source}.${policy.entity}` : policy.entity;
        if (!window.confirm(`Удалить политику кэша ${label}?`))
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
    const sourceVisible = isEditing
        ? requiresSource(editingPolicy?.entity ?? form.entity)
        : requiresSource(form.entity);

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
                        const isDeleting = deleting.has(policy.id);
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
                                        disabled={ isSaving || isDeleting || isInvalidating || loading }
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
                { sourceVisible && (
                    <label>
                        Source
                        <select
                            value={ form.source ?? "" }
                            onChange={ (e) =>
                                setForm({ ...form, source: e.target.value || null }) }
                            disabled={ isEditing }
                            required
                        >
                            <option value="" disabled>
                                Выберите source
                            </option>
                            { CACHE_SOURCES.map((s) => (
                                <option key={ s.value } value={ s.value }>
                                    { s.label }
                                </option>
                            )) }
                        </select>
                    </label>
                ) }
                <label>
                    Entity
                    <select
                        value={ form.entity }
                        onChange={ (e) => handleEntityChange(e.target.value) }
                        disabled={ isEditing }
                    >
                        { [ ...MULTI_SOURCE_ENTITIES, ...SINGLE_SOURCE_ENTITIES ].map((e) => (
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
                            setForm({ ...form, ttl: Number(e.target.value) || 3600 }) }
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
