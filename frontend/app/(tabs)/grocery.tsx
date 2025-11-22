import React, { useState, useCallback } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { Appbar, Card, Text, Checkbox, IconButton, FAB, useTheme, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import api from '../../api';
import Config from '@/constants/Config';

export default function GroceryScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const theme = useTheme();
  const router = useRouter();

  const fetchGroceryList = async () => {
    try {
      const res = await api.get('/grocery/', {
        params: { user_id: Config.TEST_USER_ID, show_purchased: true }
      });
      setItems(res.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchGroceryList();
    }, [])
  );

  const togglePurchased = async (itemId: string, currentStatus: boolean) => {
    // Optimistic update
    setItems(prev => prev.map(i =>
      i.grocery_item_id === itemId ? { ...i, is_purchased: !currentStatus } : i
    ));

    try {
      await api.put(`/grocery/${itemId}/toggle`, {}, {
        params: { user_id: Config.TEST_USER_ID }
      });
    } catch (error) {
      console.error(error);
      fetchGroceryList(); // Revert on error
    }
  };

const clearPurchased = async () => {
    Alert.alert(
      "Finish Shopping?",
      "Purchased items will be moved to your fridge inventory.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Confirm",
          onPress: async () => {
            try {
              const res = await api.post('/grocery/checkout', {}, {
                params: { user_id: Config.TEST_USER_ID }
              });

              fetchGroceryList(); // Refresh list
              Alert.alert("Done!", res.data.message); // Show backend success message
            } catch (error: any) {
              // Handle specific error where no items are selected
              if (error.response && error.response.status === 400) {
                Alert.alert("Info", "No purchased items selected.");
              } else {
                console.error(error);
                Alert.alert("Error", "Failed to checkout.");
              }
            }
          }
        }
      ]
    );
  };

  const renderItem = ({ item }: { item: any }) => (
    <Card
      style={[styles.card, item.is_purchased && styles.purchasedCard]}
      onPress={() => togglePurchased(item.grocery_item_id, item.is_purchased)} // Make whole card tappable
    >
      <Card.Content style={styles.cardRow}>
        {/* REPLACED Checkbox with IconButton for better visibility */}
        <IconButton
          icon={item.is_purchased ? "checkbox-marked" : "checkbox-blank-outline"}
          iconColor={item.is_purchased ? theme.colors.primary : '#666'}
          size={24}
          onPress={() => togglePurchased(item.grocery_item_id, item.is_purchased)}
        />

        <View style={styles.info}>
          <Text
            variant="titleMedium"
            style={[styles.text, item.is_purchased && styles.strikethrough]}
          >
            {item.food_name}
          </Text>
          <Text variant="bodySmall" style={styles.details}>
            {item.quantity_needed} {item.unit} • {item.reason === 'recipe_requirement' ? 'For Recipe' : 'Manual'}
          </Text>
        </View>
      </Card.Content>
    </Card>
  );

  const purchasedCount = items.filter(i => i.is_purchased).length;

  return (
    <SafeAreaView style={styles.container}>
      <Appbar.Header mode="center-aligned" elevated>
        <Appbar.Content title="Grocery List" />
        {purchasedCount > 0 && (
          <Appbar.Action icon="check-all" onPress={clearPurchased} />
        )}
      </Appbar.Header>

      <FlatList
        data={items}
        keyExtractor={(item) => item.grocery_item_id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchGroceryList(); }} />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.center}>
              <Text>Your list is empty.</Text>
              <Text variant="bodySmall">Plan a meal to generate items!</Text>
            </View>
          ) : null
        }
      />

      {/* Manual Add Button */}
      <FAB
        icon="plus"
        style={styles.fab}
        onPress={() => Alert.alert("Coming Soon", "Use the Recipe feature to generate items automatically!")}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  list: { padding: 16 },
  card: { marginBottom: 12, backgroundColor: 'white' },
  purchasedCard: { opacity: 0.6, backgroundColor: '#f0f0f0' },
  cardRow: { flexDirection: 'row', alignItems: 'center' },
  info: { marginLeft: 10, flex: 1 },
  text: { fontWeight: '500' },
  strikethrough: { textDecorationLine: 'line-through', color: '#888' },
  details: { color: '#666' },
  center: { alignItems: 'center', marginTop: 50 },
  fab: { position: 'absolute', margin: 16, right: 0, bottom: 0, backgroundColor: '#2196F3' },
});