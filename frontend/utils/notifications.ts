import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Helper to calculate days difference in LOCAL time
const getDaysUntil = (dateString: string) => {
  const parts = dateString.split('-');
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  const target = new Date(year, month, day);

  const now = new Date();
  now.setHours(0, 0, 0, 0);

  const diffTime = target.getTime() - now.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

export const scheduleExpiryNotifications = async (inventoryItems: any[]) => {
  const HISTORY_KEY = 'NOTIFIED_HISTORY';
  const rawHistory = await AsyncStorage.getItem(HISTORY_KEY);
  const history = rawHistory ? JSON.parse(rawHistory) : {};
  const todayStr = new Date().toISOString().split('T')[0];

  // Cancel pending to avoid duplicates (does not clear delivered tray notifications)
  await Notifications.cancelAllScheduledNotificationsAsync();

  let scheduledCount = 0;

  for (const item of inventoryItems) {
    const daysLeft = getDaysUntil(item.expiry_date);
    const notificationKey = `${item.inventory_id}_${todayStr}`;

    // Logic: Notify if expiring in the next 3 days
    if (daysLeft >= 0 && daysLeft <= 3) {
      // Anti-Spam Check: Skip if already notified today
      if (history[notificationKey]) {
        console.log(`Skipping ${item.food_name} (Already notified today)`);
        continue;
      }

      await Notifications.scheduleNotificationAsync({
        content: {
          title: "Food Expiry Warning ⚠️",
          body: `Your ${item.food_name} is expiring in ${daysLeft === 0 ? 'today' : daysLeft + ' days'}! Use it soon.`,
          sound: true,
        },
        trigger: {
          // Type-Safe Trigger Configuration
          type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
          seconds: 5 + (scheduledCount * 2), // 5s delay for Demo
          repeats: false,
        },
      });

      // Mark as notified
      history[notificationKey] = true;
      scheduledCount++;
    }
  }

  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  console.log(`Scheduled ${scheduledCount} NEW notifications.`);
};