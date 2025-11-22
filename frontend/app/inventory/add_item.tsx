import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import { TextInput, Button, Text, SegmentedButtons, ActivityIndicator } from 'react-native-paper';
import { useRouter, useLocalSearchParams, Stack } from 'expo-router';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../../api';
import Config from '../../constants/Config';
import { convertUnit } from '../../utils/units'; // Ensure this import exists

export default function AddItemScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();

  // Detect Mode: 'inventory' (default) or 'grocery'
  const mode = params.mode === 'grocery' ? 'grocery' : 'inventory';
  const isGrocery = mode === 'grocery';
  const isEditing = !!params.inventoryId;

  // Form State
  const [foodId, setFoodId] = useState(params.foodId as string || '');
  const [foodName, setFoodName] = useState(params.foodName as string || '');
  const [quantity, setQuantity] = useState('1');
  const [unit, setUnit] = useState('count');

  // Inventory-specific State
  const [expiryDate, setExpiryDate] = useState(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000));
  const [storageLocation, setStorageLocation] = useState('fridge');

  // UI State
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [unitSystem, setUnitSystem] = useState<'metric' | 'imperial'>('metric');

  // 1. Load User Unit Preference on Mount
  useEffect(() => {
    AsyncStorage.getItem('UNIT_PREFERENCE').then(val => {
      if (val) setUnitSystem(val as 'metric' | 'imperial');
    });
  }, []);

  // 2. Handle Edit Mode (Pre-fill Data)
  useEffect(() => {
    if (isEditing) {
      // Ensure quantity is treated as string for input
      const initialQty = params.initialQuantity as string;
      const initialUnit = params.initialUnit as string;

      // If user is in Imperial mode, convert the stored Metric value to Imperial for display
      if (unitSystem === 'imperial' && initialUnit === 'g') {
        // Simple inline conversion for display (reverse of save logic)
        // Real app might want a dedicated helper for this direction too
        const converted = parseFloat(initialQty) * 0.035274;
        setQuantity(converted.toFixed(2));
        setUnit('oz');
      } else {
        setQuantity(initialQty);
        setUnit(initialUnit);
      }

      if (params.initialLocation) setStorageLocation(params.initialLocation as string);
      if (params.initialExpiry) setExpiryDate(new Date(params.initialExpiry as string));
    }
  }, [isEditing, unitSystem]); // Re-run if unit system loads after params

  // --- SEARCH LOGIC ---
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

  // --- SAVE LOGIC ---
  const handleSave = async () => {
    if (!foodId && !isEditing) {
      Alert.alert("Error", "Please select a food item first.");
      return;
    }

    setLoading(true);

    // Convert BACK to Metric for Database if needed
    let dbQuantity = parseFloat(quantity);
    let dbUnit = unit;

    // Basic reverse conversion for saving
    if (unit === 'oz') {
      dbQuantity = dbQuantity / 0.035274; // Convert oz -> g
      dbUnit = 'g';
    } else if (unit === 'lb') {
      dbQuantity = dbQuantity / 2.20462; // Convert lb -> kg
      dbUnit = 'kg';
    }

    try {
      if (isGrocery) {
        // --- GROCERY SAVE ---
        await api.post('/grocery/items', {
          food_id: foodId,
          quantity: dbQuantity,
          unit: dbUnit,
          reason: 'need_more'
        }, {
          params: { user_id: Config.TEST_USER_ID }
        });
        Alert.alert("Success", "Added to Grocery List!");

        if (router.canDismiss()) router.dismissAll();
        router.replace('/(tabs)/grocery');

      } else {
        // --- INVENTORY SAVE ---
        const payload = {
          quantity: dbQuantity,
          unit: dbUnit,
          expiry_date: expiryDate.toISOString().split('T')[0],
          storage_location: storageLocation,
          notes: "Added/Edited via FreshMind App"
        };

        if (isEditing) {
          // Update existing
          await api.put(`/inventory/items/${params.inventoryId}`, payload, {
            params: { user_id: Config.TEST_USER_ID }
          });
          Alert.alert("Updated", "Item updated successfully!");
        } else {
          // Create new
          await api.post('/inventory/items', {
            food_id: foodId,
            ...payload
          }, { params: { user_id: Config.TEST_USER_ID } });
          Alert.alert("Success", "Item added to inventory!");
        }

        if (router.canDismiss()) router.dismissAll();
        router.replace('/(tabs)');
      }

    } catch (error) {
      Alert.alert("Error", "Could not save item.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Custom Header Configuration */}
      <Stack.Screen
        options={{
          title: isGrocery ? 'Add to Grocery List' : (isEditing ? 'Edit Item' : 'Add Item'),
          headerBackTitle: 'Back', // Fixes the "(tabs)" issue
        }}
      />

      <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>

        {/* 1. Food Selection (Hide in Edit Mode) */}
        {!isEditing && !foodId && (
          <View style={{ marginBottom: 20 }}>
            <TextInput
              label="Search Food"
              value={searchQuery}
              onChangeText={(text) => { setSearchQuery(text); searchFood(text); }}
              mode="outlined"
              placeholder="e.g. Milk, Bread, Eggs"
              right={<TextInput.Icon icon="magnify" />}
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

        {/* Selected Item Summary */}
        <View style={styles.summaryBox}>
          <Text variant="titleMedium">Item: {foodName || "No item selected"}</Text>
        </View>

        {/* 2. Quantity Form */}
        <View style={styles.formGroup}>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <View style={{ flex: 2 }}>
              <TextInput
                label="Quantity"
                value={quantity}
                onChangeText={setQuantity}
                keyboardType="numeric"
                mode="outlined"
              />
            </View>
            <View style={{ flex: 1, justifyContent: 'center' }}>
               {/* Simple Unit Toggle for MVP */}
               <Button mode="text" onPress={() => {
                 // Basic toggle for UX
                 if(unit === 'g') setUnit('kg');
                 else if(unit === 'kg') setUnit('count');
                 else if(unit === 'count') setUnit('oz'); // Imperial support
                 else if(unit === 'oz') setUnit('lb');
                 else setUnit('g');
               }}>{unit}</Button>
            </View>
          </View>

          {/* Inventory Specific Fields */}
          {!isGrocery && (
            <>
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
            </>
          )}
        </View>

        <Button
          mode="contained"
          onPress={handleSave}
          loading={loading}
          disabled={loading || (!foodId && !isEditing)}
          style={{ marginTop: 30 }}
        >
          {isGrocery ? "Add to List" : "Save Item"}
        </Button>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  summaryBox: { padding: 15, backgroundColor: '#f0f0f0', borderRadius: 8, marginBottom: 20 },
  formGroup: { gap: 15 },
  label: { marginTop: 10, marginBottom: 5, fontWeight: '600' }
});