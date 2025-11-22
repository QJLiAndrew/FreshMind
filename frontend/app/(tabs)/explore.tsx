import React, { useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl } from 'react-native';
import { Appbar, Card, Text, Chip, Button, ProgressBar, useTheme } from 'react-native-paper';
import { useRouter, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../../api';
import Config from '../../constants/Config';

export default function RecipesScreen() {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();
  const theme = useTheme();

  const fetchRecommendations = async () => {
    try {
      // Use the recommendation endpoint
      const res = await api.get('/recipes/recommend', {
        params: { user_id: Config.TEST_USER_ID, limit: 10 }
      });
      setRecommendations(res.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchRecommendations();
    }, [])
  );

  const renderItem = ({ item }: { item: any }) => {
    const { recipe, match_score, missing_ingredients } = item;

    return (
      <Card style={styles.card} onPress={() => router.push(`/recipes/${recipe.recipe_id}` as any)}>
        <Card.Cover source={{ uri: recipe.image_url || 'https://via.placeholder.com/300' }} />
        <Card.Content style={styles.content}>
          <Text variant="titleMedium" style={styles.title}>{recipe.recipe_name}</Text>

          {/* Match Score Indicator */}
          <View style={styles.matchContainer}>
            <Text variant="labelMedium" style={{ color: theme.colors.primary, fontWeight: 'bold' }}>
              {Math.round(match_score)}% Match
            </Text>
            <ProgressBar progress={match_score / 100} color={theme.colors.primary} style={styles.progress} />
          </View>

          <Text variant="bodySmall" style={styles.missing}>
            Missing: {missing_ingredients.slice(0, 3).join(', ')}
            {missing_ingredients.length > 3 ? ` +${missing_ingredients.length - 3} more` : ''}
          </Text>
        </Card.Content>
      </Card>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <Appbar.Header mode="small" elevated>
        <Appbar.Content title="What to Cook?" />
      </Appbar.Header>

      <FlatList
        data={recommendations}
        keyExtractor={(item) => item.recipe.recipe_id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchRecommendations(); }} />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.center}>
              <Text>No recommendations yet.</Text>
              <Text variant="bodySmall">Add more items to your fridge!</Text>
            </View>
          ) : null
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  list: { padding: 16 },
  card: { marginBottom: 16, backgroundColor: 'white' },
  content: { marginTop: 10 },
  title: { fontWeight: 'bold', marginBottom: 5 },
  matchContainer: { marginVertical: 8 },
  progress: { height: 6, borderRadius: 3, marginTop: 4 },
  missing: { color: '#666' },
  center: { alignItems: 'center', marginTop: 50 }
});