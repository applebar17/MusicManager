import { Folder } from "lucide-react";

type PathDisplayProps = {
  path: string;
};

export function PathDisplay({ path }: PathDisplayProps) {
  return (
    <span className="path-display" title={path}>
      <Folder size={14} />
      <span>{path}</span>
    </span>
  );
}
