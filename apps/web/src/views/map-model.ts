export interface MapCamera {
  camera_id: string;
  label: string;
  latitude: number;
  longitude: number;
  coordinate_status: string;
  location_description: string;
}

export interface MapPoint {
  sequence: number;
  camera_id: string;
  latitude: number;
  longitude: number;
  first_observed_s: number;
  identified_at_s: number;
  last_observed_s: number;
  coordinate_status: string;
  incoming_association: {
    score: number;
    score_kind: string;
    is_probability: false;
  } | null;
}

export interface MapTrajectory {
  vehicle_id: string;
  predicted_plate: string | null;
  camera_count: number;
  point_count: number;
  prediction_status: string;
  geometry_status: string;
  disclosure: string | null;
  points: MapPoint[];
}

export interface CameraMapPayload {
  run_id: string;
  scenario: string;
  location_label: string;
  location_country: string | null;
  approximate_center: {
    latitude: number;
    longitude: number;
    source: string;
  };
  coordinate_accuracy: string;
  coordinate_notice: string;
  tile_source: {
    provider: string;
    url: string;
    attribution: string;
    api_key_required: boolean;
  };
  cameras: MapCamera[];
}

export interface TrajectoryMapPayload {
  run_id: string;
  scenario: string;
  coordinate_accuracy: string;
  coordinate_notice: string;
  trajectory_geometry: string;
  ordering: string;
  prediction_status: string;
  trajectories: MapTrajectory[];
}

export interface VisibleTrajectory {
  positions: Array<[number, number]>;
  currentPosition: [number, number] | null;
  currentTime: number | null;
}

export function orderedPoints(points: MapPoint[]): MapPoint[] {
  return [...points].sort(
    (left, right) =>
      left.identified_at_s - right.identified_at_s || left.sequence - right.sequence,
  );
}

export function featuredTrajectory(trajectories: MapTrajectory[]): MapTrajectory | null {
  return [...trajectories].sort(
    (left, right) =>
      right.camera_count - left.camera_count ||
      right.point_count - left.point_count ||
      left.points[0].identified_at_s - right.points[0].identified_at_s ||
      left.vehicle_id.localeCompare(right.vehicle_id),
  )[0] ?? null;
}

export function cameraSequence(trajectory: MapTrajectory): string {
  return orderedPoints(trajectory.points)
    .map((point) => point.camera_id)
    .join(" → ");
}

export function trajectorySpanSeconds(trajectory: MapTrajectory): number {
  const points = orderedPoints(trajectory.points);
  if (!points.length) return 0;
  return Math.max(0, points[points.length - 1].last_observed_s - points[0].first_observed_s);
}

export function minimumAssociationScore(trajectory: MapTrajectory): number | null {
  const scores = trajectory.points.flatMap((point) =>
    point.incoming_association ? [point.incoming_association.score] : [],
  );
  return scores.length ? Math.min(...scores) : null;
}

export function visibleTrajectory(
  points: MapPoint[],
  progress: number,
): VisibleTrajectory {
  const ordered = orderedPoints(points);
  if (!ordered.length) {
    return { positions: [], currentPosition: null, currentTime: null };
  }
  if (ordered.length === 1) {
    const only: [number, number] = [ordered[0].latitude, ordered[0].longitude];
    return {
      positions: [only],
      currentPosition: only,
      currentTime: ordered[0].identified_at_s,
    };
  }

  const bounded = Math.min(1, Math.max(0, progress));
  const firstTime = ordered[0].identified_at_s;
  const lastTime = ordered[ordered.length - 1].identified_at_s;
  const timelineDuration = lastTime - firstTime;
  const targetTime =
    timelineDuration > 0
      ? firstTime + timelineDuration * bounded
      : firstTime + (ordered.length - 1) * bounded;
  const effectiveTime = (point: MapPoint, index: number) =>
    timelineDuration > 0 ? point.identified_at_s : firstTime + index;

  const positions: Array<[number, number]> = [
    [ordered[0].latitude, ordered[0].longitude],
  ];
  let currentPosition = positions[0];

  for (let index = 1; index < ordered.length; index += 1) {
    const previous = ordered[index - 1];
    const current = ordered[index];
    const previousTime = effectiveTime(previous, index - 1);
    const currentTime = effectiveTime(current, index);
    if (targetTime >= currentTime) {
      currentPosition = [current.latitude, current.longitude];
      positions.push(currentPosition);
      continue;
    }
    const duration = currentTime - previousTime;
    const segmentProgress = duration > 0 ? (targetTime - previousTime) / duration : 0;
    const boundedSegment = Math.min(1, Math.max(0, segmentProgress));
    currentPosition = [
      previous.latitude + (current.latitude - previous.latitude) * boundedSegment,
      previous.longitude + (current.longitude - previous.longitude) * boundedSegment,
    ];
    positions.push(currentPosition);
    break;
  }

  return { positions, currentPosition, currentTime: targetTime };
}
