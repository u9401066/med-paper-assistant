export interface Diagram {
  id: string;
  name: string;
  fileName: string;
  path: string;
  createdAt: string;
  updatedAt: string;
  thumbnail?: string;
}

export interface DiagramListResponse {
  diagrams: Diagram[];
  projectSlug: string;
}
