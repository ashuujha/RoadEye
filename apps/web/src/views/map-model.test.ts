import { describe, expect, it } from "vitest";
import {
  cameraSequence,
  featuredTrajectory,
  minimumAssociationScore,
  orderedPoints,
  trajectorySpanSeconds,
  visibleTrajectory,
  type MapPoint,
  type MapTrajectory,
} from "./map-model";

const points: MapPoint[] = [
  {
    sequence: 2,
    camera_id: "c3",
    latitude: 30,
    longitude: 30,
    first_observed_s: 20,
    identified_at_s: 30,
    last_observed_s: 31,
    coordinate_status: "approximate",
    incoming_association: null,
  },
  {
    sequence: 0,
    camera_id: "c1",
    latitude: 10,
    longitude: 10,
    first_observed_s: 9,
    identified_at_s: 10,
    last_observed_s: 11,
    coordinate_status: "approximate",
    incoming_association: null,
  },
  {
    sequence: 1,
    camera_id: "c2",
    latitude: 20,
    longitude: 20,
    first_observed_s: 14,
    identified_at_s: 20,
    last_observed_s: 21,
    coordinate_status: "approximate",
    incoming_association: null,
  },
];

describe("trajectory replay model", () => {
  it("orders points by recorded identification time", () => {
    expect(orderedPoints(points).map((point) => point.camera_id)).toEqual([
      "c1",
      "c2",
      "c3",
    ]);
  });

  it("interpolates the replay marker along the timestamp-ordered path", () => {
    const halfway = visibleTrajectory(points, 0.25);
    expect(halfway.positions).toEqual([
      [10, 10],
      [15, 15],
    ]);
    expect(halfway.currentTime).toBe(15);
  });

  it("returns the complete static path at the end of replay", () => {
    const complete = visibleTrajectory(points, 1);
    expect(complete.positions).toEqual([
      [10, 10],
      [20, 20],
      [30, 30],
    ]);
    expect(complete.currentPosition).toEqual([30, 30]);
  });
});

describe("trajectory presentation model", () => {
  const trajectory: MapTrajectory = {
    vehicle_id: "roadeye_demo",
    predicted_plate: null,
    camera_count: 3,
    point_count: 3,
    prediction_status: "UNVERIFIED",
    geometry_status: "observations_only_no_road_route_claim",
    disclosure: null,
    points: points.map((point, index) => ({
      ...point,
      incoming_association:
        index === 0
          ? null
          : { score: index === 1 ? 0.91 : 0.85, score_kind: "cosine", is_probability: false },
    })),
  };

  it("summarizes the timestamp-ordered camera route and observed span", () => {
    expect(cameraSequence(trajectory)).toBe("c1 → c2 → c3");
    expect(trajectorySpanSeconds(trajectory)).toBe(22);
    expect(minimumAssociationScore(trajectory)).toBe(0.85);
  });

  it("selects the journey with the strongest camera coverage", () => {
    const shorter = { ...trajectory, vehicle_id: "roadeye_short", camera_count: 2 };
    expect(featuredTrajectory([shorter, trajectory])?.vehicle_id).toBe("roadeye_demo");
  });
});
