const APP_ID = process.env.NEXT_PUBLIC_ONESIGNAL_APP_ID || "";
const SDK_URL = "https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js";

let initPromise = null;

export function isConfigured() {
  return Boolean(APP_ID);
}

function loadScript() {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${SDK_URL}"]`)) return resolve();
    const script = document.createElement("script");
    script.src = SDK_URL;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load the OneSignal SDK."));
    document.head.appendChild(script);
  });
}

export function initOneSignal() {
  if (!isConfigured()) return Promise.reject(new Error("OneSignal app id not set."));
  if (initPromise) return initPromise;

  initPromise = loadScript().then(
    () =>
      new Promise((resolve) => {
        window.OneSignalDeferred = window.OneSignalDeferred || [];
        window.OneSignalDeferred.push(async (OneSignal) => {
          await OneSignal.init({
            appId: APP_ID,
            allowLocalhostAsSecureOrigin: true,
          });
          resolve(OneSignal);
        });
      })
  );
  return initPromise;
}

/** Prompt for permission and return the subscription id, or throw a readable error. */
export async function subscribeToPush() {
  const OneSignal = await initOneSignal();

  if (Notification.permission === "denied") {
    throw new Error(
      "Notifications are blocked for this site. Re-allow them in your browser settings."
    );
  }

  await OneSignal.Notifications.requestPermission();

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const id = OneSignal.User?.PushSubscription?.id;
    if (id) return id;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Subscribed, but no subscription id came back. Try reloading.");
}
