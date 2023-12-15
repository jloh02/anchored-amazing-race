export function getIcon(i: number) {
  return new URL(`./assets/${i}.svg`, import.meta.url).href;
}

export function timeSince(date: Date) {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

  let interval = seconds / 31536000;

  if (interval > 1) {
    return Math.floor(interval) + " years";
  }
  interval = seconds / 2592000;
  if (interval > 1) {
    return Math.floor(interval) + " months";
  }
  interval = seconds / 86400;
  if (interval > 1) {
    return Math.floor(interval) + " days";
  }
  interval = seconds / 3600;
  if (interval > 1) {
    return Math.floor(interval) + " hours";
  }
  interval = seconds / 60;
  if (interval > 1) {
    return Math.floor(interval) + "m " + Math.floor(seconds % 60) + "s";
  }
  return Math.floor(seconds) + "s";
}

// def get_start_chall_index(direction: Direction) -> int:
//     if direction == Direction.A0:
//         return 1
//     if direction == Direction.B0:
//         return NUMBER_LOCATIONS
//     return 0
