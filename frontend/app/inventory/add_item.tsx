import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import { TextInput, Button, Text, SegmentedButtons, ActivityIndicator } from 'react-native-paper';
import { useRouter, useLocalSearchParams } from 'expo-router';
import api from '../../api';
import Config from '../../constants/Config';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';

export default function AddItemScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();

  // Form State
  const [foodId, setFoodId] = useState(params.foodId || '');
  const [foodName, setFoodName] = useState(params.foodName || '');
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('count');
  const [expiryDate, setExpiryDate] = useState(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)); // +7 days default
  const [storageLocation, setStorageLocation] = useState('fridge');
  const [loading, setLoading] = useState(false);

  // Search State (For manual entry)
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (params.inventoryId) {
      const fetchItem = async () => {
        try {
          // You might need to add this GET endpoint to backend if not exists,
          // or pass data via params. For now, let's assume we pass data via params or fetch it.
          // Simpler approach for MVP: Pass data via params from the Home Screen
          if (params.initialQuantity) setQuantity(params.initialQuantity as string);
          if (params.initialUnit) setUnit(params.initialUnit as string);
          if (params.initialLocation) setStorageLocation(params.initialLocation as string);
          if (params.initialExpiry) setExpiryDate(new Date(params.initialExpiry as string));
        } catch (e) {
          console.error(e);
        }
      };
      fetchItem();
    }
  }, [params.inventoryId]);

  // Search functionality for Manual Entry
  const searchFood = async (query: string) => {
    if (query.length < 3) return;
    setIsSearching(true);
    try {
      const res = await api.get('/inventory/search', { params: { query } });
      setSearchResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSave = async () => {
    if (!foodId) {
      Alert.alert("Error", "Please select a food item first.");
      return;
    }

    setLoading(true);
    try {
      if (params.inventoryId) {
        // EDIT MODE: PUT request
        await api.put(`/inventory/items/${params.inventoryId}`, {
          quantity: parseFloat(quantity),
          unit: unit,
          expiry_date: expiryDate.toISOString().split('T')[0],
          storage_location: storageLocation,
        }, {
          params: { user_id: Config.TEST_USER_ID }
        });
        Alert.alert("Updated", "Item updated successfully!");
      } else {
        // CREATE MODE: POST request
        await api.post('/inventory/items', {
          food_id: foodId,
          quantity: parseFloat(quantity),
          unit: unit,
          expiry_date: expiryDate.toISOString().split('T')[0],
          storage_location: storageLocation,
          notes: "Added via FreshMind App"
        }, {
          params: { user_id: Config.TEST_USER_ID }
        });
        Alert.alert("Success", "Item added to inventory!");
      }

      if (router.canDismiss()) router.dismissAll();
      router.replace('/(tabs)');

    } catch (error) {
      Alert.alert("Error", "Could not save item.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <Text variant="headlineMedium" style={{ marginBottom: 20 }}>
        {params.foodId ? 'Confirm Item' : 'Add Manual Item'}
      </Text>

      {/* 1. Food Selection (Only show if not pre-filled) */}
      {!params.foodId && (
        <View style={{ marginBottom: 20 }}>
          <TextInput
            label="Search Food (e.g. Apple)"
            value={searchQuery}
            onChangeText={(text) => { setSearchQuery(text); searchFood(text); }}
            mode="outlined"
          />
          {isSearching && <ActivityIndicator style={{ marginTop: 10 }} />}
          {searchResults.map((item: any) => (
            <Button
              key={item.food_id}
              mode="outlined"
              style={{ marginTop: 5 }}
              onPress={() => {
                setFoodId(item.food_id);
                setFoodName(item.name);
                setSearchQuery('');
                setSearchResults([]);
              }}
            >
              {item.name}
            </Button>
          ))}
        </View>
      )}

      {/* Selected Item Display */}
      <View style={styles.summaryBox}>
        <Text variant="titleMedium">Item: {foodName || "No item selected"}</Text>
      </View>

      {/* 2. Details Form */}
      <View style={styles.formGroup}>
        <TextInput
          label="Quantity"
          value={quantity}
          onChangeText={setQuantity}
          keyboardType="numeric"
          mode="outlined"
          right={<TextInput.Affix text={unit} />}
        />

        <Text style={styles.label}>Storage Location</Text>
        <SegmentedButtons
          value={storageLocation}
          onValueChange={setStorageLocation}
          buttons={[
            { value: 'fridge', label: 'Fridge' },
            { value: 'pantry', label: 'Pantry' },
            { value: 'freezer', label: 'Freezer' },
          ]}
        />

        <Text style={styles.label}>Expiry Date</Text>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <DateTimePicker
            value={expiryDate}
            mode="date"
            display="default"
            onChange={(e: DateTimePickerEvent, date?: Date) => {
              if (date) setExpiryDate(date);
            }}
          />
        </View>
      </View>

      <Button
        mode="contained"
        onPress={handleSave}
        loading={loading}
        disabled={loading || !foodId}
        style={{ marginTop: 30 }}
      >
        Save to Inventory
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  summaryBox: { padding: 15, backgroundColor: '#f0f0f0', borderRadius: 8, marginBottom: 20 },
  formGroup: { gap: 15 },
  label: { marginTop: 10, marginBottom: 5, fontWeight: '600' }
});