import React, { useState, useEffect, useCallback } from 'react';
import { StyleSheet, View, FlatList, RefreshControl, Image, Alert } from 'react-native';
import { Text, Card, Chip, FAB, ActivityIndicator, Appbar, useTheme } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import api from '../../api'; // Import API helper
import Config from '@/constants/Config';


// Define what an Inventory Item looks like
interface InventoryItem {
  inventory_id: string;
  food_name: string;
  food_image_url: string | null;
  quantity: number;
  unit: string;
  expiry_date: string;
  freshness_status: 'fresh' | 'consume_soon' | 'expiring_soon' | 'expired';
  days_until_expiry: number;
  storage_location?: string; // <--- Added this line
}

export default function SmartFridgeScreen() {
  const [items, setItems] = useState<InventoryItem[]>();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();
  const theme = useTheme();



  const fetchInventory = async () => {
    try {
      const response = await api.get('/inventory/items', {
        params: { user_id: Config.TEST_USER_ID } // Use Config
      });
      setItems(response.data.items);
    } catch (error) {
      console.error("Failed to fetch inventory:", error);
      // Ideally show a Snackbar error here
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Refresh data whenever the screen comes into focus (e.g. after scanning)
  useFocusEffect(
    useCallback(() => {
      fetchInventory();
    }, [])
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'fresh': return '#4CAF50'; // Green
      case 'consume_soon': return '#FF9800'; // Orange
      case 'expiring_soon': return '#F44336'; // Red
      case 'expired': return '#9E9E9E'; // Grey
      default: return theme.colors.primary;
    }
  };

  const renderItem = ({ item }: { item: InventoryItem }) => (
    <Card style={styles.card}>
      <Card.Content style={styles.cardContent}>
        {/* Left: Image */}
        {item.food_image_url ? (
          <Image source={{ uri: item.food_image_url }} style={styles.foodImage} />
        ) : (
          <View style={[styles.foodImage, { backgroundColor: '#eee', justifyContent: 'center', alignItems: 'center' }]}>
            <Text variant="labelLarge">?</Text>
          </View>
        )}

        {/* Center: Info */}
        <View style={styles.infoContainer}>
          <Text variant="titleMedium" numberOfLines={1}>{item.food_name}</Text>
          <Text variant="bodyMedium" style={{ color: '#666' }}>
            {item.quantity} {item.unit} • {item.storage_location || 'Fridge'}
          </Text>
        </View>

        {/* Right: Status Chip */}
        <View style={{ alignItems: 'flex-end' }}>
           <Chip
             textStyle={{ color: 'white', fontSize: 10 }}
             style={{ backgroundColor: getStatusColor(item.freshness_status), height: 24 }}
           >
             {item.days_until_expiry} days
           </Chip>
           <Text variant="labelSmall" style={{ marginTop: 4 }}>
             {item.expiry_date}
           </Text>
        </View>
      </Card.Content>
    </Card>
  );

  return (
    <SafeAreaView style={styles.container}>
      <Appbar.Header mode="center-aligned" elevated>
        <Appbar.Content title="My Smart Fridge" />
        <Appbar.Action icon="refresh" onPress={fetchInventory} />
      </Appbar.Header>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.inventory_id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchInventory(); }} />
          }
          ListEmptyComponent={
            <View style={styles.center}>
              <Text>Your fridge is empty!</Text>
              <Text>Scan an item to get started.</Text>
            </View>
          }
        />
      )}

      {/* Floating Action Button to Scan */}
    <FAB
      icon="plus"
      label="Add Item"
      style={styles.fab}
      onPress={() => {
        Alert.alert("Add Item", "Choose method", [
          { text: "Scan Barcode", onPress: () => router.push('/scanner') },
          // FIX: Add 'as any' to bypass strict route checking temporarily
          { text: "Manual Search", onPress: () => router.push('/inventory/add_item' as any) },
          { text: "Cancel", style: "cancel" }
        ])
      }}
    />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  list: {
    padding: 16,
    paddingBottom: 80, // Space for FAB
  },
  card: {
    marginBottom: 12,
    backgroundColor: 'white',
  },
  cardContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  foodImage: {
    width: 50,
    height: 50,
    borderRadius: 8,
    marginRight: 16,
  },
  infoContainer: {
    flex: 1,
    marginRight: 8,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 50,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: '#2196F3', // Brand color
  },
});