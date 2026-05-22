export type MatchStatus = "matched" | "missing_audio" | "ambiguous" | "manually_mapped";

export type MatchCandidate = {
  songId: string;
  audioFileId: string;
  confidence: number;
  status: MatchStatus;
};

