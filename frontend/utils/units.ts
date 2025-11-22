export const convertUnit = (quantity: number | string, unit: string, system: 'metric' | 'imperial') => {
  // 1. Force conversion to number (Handle backend sending strings)
  const qty = typeof quantity === 'string' ? parseFloat(quantity) : quantity;

  // 2. If Metric, return as-is (but ensured as number)
  if (system === 'metric') {
    return { quantity: qty, unit };
  }

  // 3. Imperial Conversions
  let newQuantity = qty;
  let newUnit = unit;

  switch (unit.toLowerCase()) {
    case 'g':
    case 'gram':
    case 'grams':
      newQuantity = qty * 0.035274;
      newUnit = 'oz';
      break;
    case 'kg':
    case 'kilogram':
      newQuantity = qty * 2.20462;
      newUnit = 'lb';
      break;
    case 'ml':
    case 'milliliter':
      newQuantity = qty * 0.033814;
      newUnit = 'fl oz';
      break;
    case 'l':
    case 'liter':
      newQuantity = qty * 33.814;
      newUnit = 'fl oz';
      break;
    default:
      // 'count', 'unit', etc. stay the same
      break;
  }

  // 4. Safe formatting
  return {
    quantity: parseFloat(newQuantity.toFixed(2)),
    unit: newUnit
  };
};