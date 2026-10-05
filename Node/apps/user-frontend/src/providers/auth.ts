import { useDemoAuth } from "@/stores/demoAuth";
import { useFeatureFlags } from "@/stores/featureFlags";
import { useUser } from "@/stores/user";
import { useRouter } from "@/stores/router";
import { gotoAuthForm, gotoHome } from "@/services/redirects";
import { updateUser } from "@/services/auth";
import { watch } from "vue";

import type { IUser } from "@/interfaces/User";
import type { RouteRecordNameGeneric } from "vue-router";

export function mountAuthProvider() {
    watch(
        [
            () => useUser().user,
            () => useRouter().getCurrentRoute()?.value?.name,
        ],
        (
            [newUser, newRouteName]
        ) => provideUser(newUser, newRouteName),
        { immediate: true },
    );

    watch(() => useDemoAuth().demoUid, async (newUid: string | null) => {
        const headers: Record<string, string> = {};
        if (newUid) headers["X-Demo-User-UID"] = newUid;

        // TODO: Update feature flags when URL is changed, not demo UID; in other provider
        try {
            const res = await fetch("/api/v2/demo/feature-flags", { headers });
            if (res.ok) {
                const ff = await res.json() as { blurred_fields: string[] };
                useFeatureFlags().setBlurredFields(ff.blurred_fields ?? []);
            }
        } catch (e) { console.log(e); }
    }, { immediate: true });
}

async function provideUser(newUser: IUser | null, newRouteName?: RouteRecordNameGeneric) {
    if (!newRouteName || newRouteName === "demo" || newRouteName === "demo-route" || newRouteName === "demo-collection")
        return;

    useDemoAuth().clearDemo();

    if (newRouteName === "calculator" && !newUser)
        try {
            await updateUser();
        } catch (e) {
            console.log(e);
            gotoAuthForm();
        }
    else if (newRouteName === "login" && newUser)
        gotoHome();
}
