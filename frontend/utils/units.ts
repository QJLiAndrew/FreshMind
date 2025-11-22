export const convertUnit = (quantity: number, unit: string, system: 'metric' | 'imperial') => {
  if (system === 'metric') {
    return { quantity, unit };
  }

  // Imperial Conversions
  // 1 g = 0.035274 oz
  // 1 kg = 2.20462 lb
  // 1 ml = 0.033814 fl oz

  let newQuantity = quantity;
  let newUnit = unit;

  switch (unit.toLowerCase()) {
    case 'g':
    case 'gram':
    case 'grams':
      newQuantity = quantity * 0.035274;
      newUnit = 'oz';
      break;
    case 'kg':
    case 'kilogram':
      newQuantity = quantity * 2.20462;
      newUnit = 'lb';
      break;
    case 'ml':
    case 'milliliter':
      newQuantity = quantity * 0.033814;
      newUnit = 'fl oz';
      break;
    case 'l':
    case 'liter':
      newQuantity = quantity * 33.814;
      newUnit = 'fl oz';
      break;
    default:
      // 'count', 'unit', etc. stay the same
      break;
  }

  // Round nicely (e.g. 12.05 oz)
  return {
    quantity: parseFloat(newQuantity.toFixed(2)),
    unit: newUnit
  };
};