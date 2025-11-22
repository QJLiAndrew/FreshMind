import React, { useEffect, useState } from 'react';
import { ScrollView, View, StyleSheet, Image, Alert } from 'react-native';
import { Text, ActivityIndicator, Chip, Divider, List, Button, useTheme } from 'react-native-paper';
import { useLocalSearchParams, Stack } from 'expo-router';
import api from '../../api';
import Config from '../../constants/Config';

export default function RecipeDetailScreen() {
  const { id } = useLocalSearchParams(); // Gets the [id] from the URL
  const [recipe, setRecipe] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [addingToGrocery, setAddingToGrocery] = useState(false);
  const theme = useTheme();

  // Fetch recipe details when screen loads
  useEffect(() => {
    fetchRecipeDetails();
  }, [id]);

  const fetchRecipeDetails = async () => {
    try {
      const res = await api.get(`/recipes/${id}`);
      setRecipe(res.data);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Could not load recipe details.");
    } finally {
      setLoading(false);
    }
  };

  // Logic to add missing ingredients to grocery list
  const addToGroceryList = async () => {
    setAddingToGrocery(true);
    try {
      const res = await api.post(`/grocery/generate/${recipe.recipe_id}`, {}, {
        params: { user_id: Config.TEST_USER_ID }
      });

      const addedCount = res.data.items_added.length;

      if (addedCount > 0) {
        Alert.alert(
          "Success",
          `Added ${addedCount} missing items to your grocery list:\n\n- ${res.data.items_added.join('\n- ')}`
        );
      } else {
        Alert.alert("You're Good!", "You already have all the ingredients for this recipe.");
      }
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Failed to update grocery list.");
    } finally {
      setAddingToGrocery(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!recipe) {
    return (
      <View style={styles.center}>
        <Text>Recipe not found</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: recipe.recipe_name }} />
      <ScrollView style={styles.container}>
        {/* Hero Image */}
        {recipe.image_url && (
          <Image source={{ uri: recipe.image_url }} style={styles.image} />
        )}

        <View style={styles.content}>
          <Text variant="headlineMedium" style={styles.title}>{recipe.recipe_name}</Text>

          {/* Quick Stats Chips */}
          <View style={styles.chips}>
            <Chip icon="clock-outline" style={styles.chip}>{recipe.total_time_minutes || 30} min</Chip>
            <Chip icon="fire" style={styles.chip}>{Math.round(recipe.calories_per_serving || 0)} kcal</Chip>
            <Chip icon="silverware-fork-knife" style={styles.chip}>{recipe.servings} servings</Chip>
          </View>

          <Divider style={styles.divider} />

          {/* Ingredients List */}
          <Text variant="titleLarge" style={styles.sectionTitle}>Ingredients</Text>
          {recipe.ingredients.map((ing: any, index: number) => (
            <List.Item
              key={index}
              title={`${ing.quantity} ${ing.unit} ${ing.food_name}`}
              description={ing.ingredient_note}
              left={props => <List.Icon {...props} icon="circle-small" />}
            />
          ))}

          <Divider style={styles.divider} />

          {/* Instructions */}
          <Text variant="titleLarge" style={styles.sectionTitle}>Instructions</Text>
          <Text style={styles.instructions}>{recipe.instructions || "No instructions provided."}</Text>

          {/* Smart Action Button */}
          <Button
            mode="contained"
            style={styles.button}
            contentStyle={{ height: 50 }}
            icon="cart-plus"
            onPress={addToGroceryList}
            loading={addingToGrocery}
            disabled={addingToGrocery}
          >
            Add Missing to Grocery List
          </Button>
        </View>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'white' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  image: { width: '100%', height: 250 },
  content: { padding: 20 },
  title: { fontWeight: 'bold', marginBottom: 10 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  chip: { backgroundColor: '#e0e0e0' },
  divider: { marginVertical: 20 },
  sectionTitle: { fontWeight: 'bold', marginBottom: 10 },
  instructions: { lineHeight: 24, fontSize: 16 },
  button: { marginTop: 30, marginBottom: 40 }
});