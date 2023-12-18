export function getIcon(i: number, outline?: boolean) {
  if (i > 16) {
    i %= 16;
    i++;
  }

  return new URL(
    `./assets/${i}${outline ? "_outline" : ""}.svg`,
    import.meta.url
  ).href;
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

const NUMBER_LOCATIONS = 4;

function getStartChallIndex(dir: string): number {
  if (dir === "A0") return 1;
  if (dir === "B0") return NUMBER_LOCATIONS;
  return 0;
}

export interface Group {
  key?: number;
  name: string;
  current_location?: number;
  direction?: string;
  race_completed?: boolean;
  start_time?: Date;
}

export function getProgress(group: Group): number {
  if (
    !group.start_time ||
    !group.direction ||
    group.current_location === undefined
  )
    return -1;
  if ("end_time" in group) return NUMBER_LOCATIONS + 1;

  return Math.abs(
    (group.current_location - getStartChallIndex(group.direction)) *
      (group.direction.at(0) === "B" ? -1 : 1)
  );
}

export function getProgressStr(group: Group): string {
  const progress = getProgress(group);

  if (progress === -1) return "Have not started";
  if (progress === NUMBER_LOCATIONS + 1) return "Finished race";
  return `${progress} locations finished`;
}
