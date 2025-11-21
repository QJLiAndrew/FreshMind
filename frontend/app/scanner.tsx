import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, Alert, Vibration } from 'react-native';
import { Text, Button, ActivityIndicator, IconButton } from 'react-native-paper';
import { CameraView, useCameraPermissions } from 'expo-camera'; // Updated for Expo SDK 52
import { useRouter } from 'expo-router';
import api from '../api';
import Config from '@/constants/Config';
import { Href } from 'expo-router';

export default function ScannerScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);
  const qrLock = useRef(false);
  const router = useRouter();


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
    if (data && !qrLock.current) {
      qrLock.current = true;
      setScanned(true);
      Vibration.vibrate();
      setLoading(true);

      try {
        console.log(`Scanned barcode: ${data}`);
        const scanResponse = await api.post('/inventory/scan', { barcode: data });

        if (!scanResponse.data.found) {
          Alert.alert("Not Found", "Item not in database.", [
            {
              text: "OK",
              onPress: () => {
                setScanned(false);
                setLoading(false);
                qrLock.current = false;
              }
            }
          ]);
          return;
        }

        const foodItem = scanResponse.data.food_item;
        const foodName = foodItem.name || "Unknown Item";
        const foodId = foodItem.food_id;

        Alert.alert(
          "Item Found!",
          `Do you want to add '${foodName}'?`,
          [
            {
              text: "Cancel",
              style: "cancel",
              onPress: () => {
                setScanned(false);
                setLoading(false);
                qrLock.current = false;
              }
            },
            {
              text: "Configure & Add",
              onPress: () => proceedToAddItem(foodId, foodName)
            }
          ]
        );

      } catch (error) {
        console.error(error);
        Alert.alert("Error", "Failed to fetch product data.");
        setScanned(false);
        setLoading(false);
        qrLock.current = false;
      }
    }
  };

  const proceedToAddItem = (foodId: string, foodName: string) => {
    qrLock.current = false;
    setScanned(false);
    setLoading(false);

    router.push({
      pathname: '/inventory/add_item',
      params: { foodId, foodName }
    } as any);
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