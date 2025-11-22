import React, { useState, useEffect } from 'react';
import { ScrollView, View, StyleSheet, Alert } from 'react-native';
import { Appbar, List, Switch, Button, Text, Divider, ActivityIndicator, Avatar, useTheme } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../../api';
import Config from '@/constants/Config';

export default function ProfileScreen() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const theme = useTheme();

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get(`/users/${Config.TEST_USER_ID}`);
      setProfile(res.data);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const togglePreference = async (key: string, value: boolean) => {
    // Optimistic UI update
    const updatedProfile = { ...profile, [key]: value };
    setProfile(updatedProfile);

    setSaving(true);
    try {
      // Send PATCH request
      await api.patch(`/users/${Config.TEST_USER_ID}`, { [key]: value });
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Failed to update preference");
      fetchProfile(); // Revert on error
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <View style={styles.center}><ActivityIndicator /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <Appbar.Header mode="center-aligned" elevated>
        <Appbar.Content title="My Profile" />
      </Appbar.Header>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* User Header */}
        <View style={styles.header}>
          <Avatar.Text size={80} label={profile?.username?.substring(0, 2).toUpperCase() || "U"} />
          <Text variant="headlineSmall" style={{ marginTop: 10 }}>{profile?.username}</Text>
          <Text variant="bodyMedium" style={{ color: 'gray' }}>{profile?.email}</Text>
        </View>

        <Divider />

        <List.Section>
          <List.Subheader>Dietary Preferences</List.Subheader>
          <Text style={styles.hint}>Recipes will be automatically filtered based on these settings.</Text>

          <List.Item
            title="Vegan"
            left={() => <List.Icon icon="leaf" />}
            right={() => (
              <Switch
                value={profile?.is_vegan}
                onValueChange={(val) => togglePreference('is_vegan', val)}
              />
            )}
          />
          <List.Item
            title="Vegetarian"
            left={() => <List.Icon icon="carrot" />}
            right={() => (
              <Switch
                value={profile?.is_vegetarian}
                onValueChange={(val) => togglePreference('is_vegetarian', val)}
              />
            )}
          />
          <List.Item
            title="Gluten Free"
            left={() => <List.Icon icon="barley-off" />}
            right={() => (
              <Switch
                value={profile?.is_gluten_free}
                onValueChange={(val) => togglePreference('is_gluten_free', val)}
              />
            )}
          />
          <List.Item
            title="Dairy Free"
            left={() => <List.Icon icon="cup-off" />} // Material icon name
            right={() => (
              <Switch
                value={profile?.is_dairy_free}
                onValueChange={(val) => togglePreference('is_dairy_free', val)}
              />
            )}
          />
          <List.Item
            title="Halal"
            left={() => <List.Icon icon="check-decagram" />} // Placeholder icon
            right={() => (
              <Switch
                value={profile?.is_halal}
                onValueChange={(val) => togglePreference('is_halal', val)}
              />
            )}
          />
          <List.Item
            title="Kosher"
            left={() => <List.Icon icon="star-david" />} // Material icon name
            right={() => (
              <Switch
                value={profile?.is_kosher}
                onValueChange={(val) => togglePreference('is_kosher', val)}
              />
            )}
          />
        </List.Section>

        <Divider />

        <View style={{ padding: 20 }}>
          <Button mode="outlined" onPress={() => Alert.alert("Log Out", "This is a demo app.")}>
            Log Out
          </Button>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scrollContent: { paddingBottom: 20 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { alignItems: 'center', padding: 20 },
  hint: { paddingHorizontal: 16, paddingBottom: 10, color: 'gray', fontSize: 12 },
});