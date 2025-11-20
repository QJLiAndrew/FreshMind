import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Alert, Vibration } from 'react-native';
import { Text, Button, ActivityIndicator, IconButton } from 'react-native-paper';
import { CameraView, useCameraPermissions } from 'expo-camera'; // Updated for Expo SDK 52
import { useRouter } from 'expo-router';
import api from '../api';

export default function ScannerScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // REPLACE WITH YOUR REAL USER ID
  const TEST_USER_ID = "REPLACE_WITH_YOUR_USER_UUID";

  if (!permission) {
    // Camera permissions are still loading
    return <View />;
  }

  if (!permission.granted) {
    // Camera permissions are not granted yet
    return (
      <View style={styles.container}>
        <Text style={{ textAlign: 'center', marginBottom: 20 }}>
          We need your permission to show the camera
        </Text>
        <Button mode="contained" onPress={requestPermission}>
          Grant Permission
        </Button>
      </View>
    );
  }

  const handleBarCodeScanned = async ({ type, data }: { type: string; data: string }) => {
    if (scanned || loading) return;

    setScanned(true);
    Vibration.vibrate();
    setLoading(true);

    try {
      console.log(`Scanned barcode: ${data}`);

      // 1. Check/Create Food Item in Backend
      const scanResponse = await api.post('/inventory/scan', { barcode: data });

      if (!scanResponse.data.found) {
        Alert.alert("Not Found", "This item is not in our database yet.");
        setScanned(false);
        setLoading(false);
        return;
      }

      const foodItem = scanResponse.data.food_item;
      const foodName = foodItem.name || "Unknown Item";
      const foodId = foodItem.food_id;

      // 2. Ask User to Confirm Adding
      Alert.alert(
        "Item Found!",
        `Do you want to add '${foodName}' to your fridge?`,
        [
          {
            text: "Cancel",
            style: "cancel",
            onPress: () => {
              setScanned(false);
              setLoading(false);
            }
          },
          {
            text: "Add to Fridge",
            onPress: async () => {
              await addToFridge(foodId, foodName);
            }
          }
        ]
      );

    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Failed to fetch product data. Check your server connection.");
      setScanned(false);
      setLoading(false);
    }
  };

  const addToFridge = async (foodId: string, foodName: string) => {
    try {
      // 3. Add to User Inventory
      await api.post('/inventory/items',
        {
          food_id: foodId,
          quantity: 1,
          unit: 'unit',
          expiry_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Default 7 days from now
          storage_location: 'fridge'
        },
        {
          params: { user_id: TEST_USER_ID }
        }
      );

      Alert.alert("Success", `${foodName} added to your fridge!`);
      router.back(); // Go back to Home Screen
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Could not save item to inventory.");
      setScanned(false);
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Close Button */}
      <IconButton
        icon="close"
        iconColor="white"
        size={30}
        style={styles.closeButton}
        onPress={() => router.back()}
      />

      <CameraView
        style={StyleSheet.absoluteFillObject}
        onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
        barcodeScannerSettings={{
          barcodeTypes: ["qr", "ean13", "ean8", "upc_e", "upc_a"],
        }}
      />

      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#fff" />
          <Text style={{ color: 'white', marginTop: 10 }}>Looking up product...</Text>
        </View>
      )}

      {!scanned && !loading && (
        <View style={styles.overlay}>
          <Text style={styles.scanText}>Scan a food barcode</Text>
          <View style={styles.targetBox} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    backgroundColor: 'black',
  },
  closeButton: {
    position: 'absolute',
    top: 40,
    right: 20,
    zIndex: 2,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 3,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanText: {
    color: 'white',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 50,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: -1, height: 1 },
    textShadowRadius: 10
  },
  targetBox: {
    width: 250,
    height: 250,
    borderWidth: 2,
    borderColor: '#2196F3',
    backgroundColor: 'transparent',
    borderRadius: 20,
  },
});