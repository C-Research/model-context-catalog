interface Props {
  groups: string[];
  selected: Set<string>;
  onToggle: (group: string) => void;
}

// Empty `selected` means "no filter" (show everything) — toggling a chip on
// narrows the listing to tools in at least one selected group.
export function GroupFilter({ groups, selected, onToggle }: Props) {
  return (
    <div className="group-filter" role="group" aria-label="Filter by tool group">
      {groups.map((group) => {
        const active = selected.has(group);
        return (
          <button
            key={group}
            type="button"
            className={`group-filter__chip${active ? " badge group-filter__chip--active" : ""}`}
            aria-pressed={active}
            onClick={() => onToggle(group)}
          >
            {group}
          </button>
        );
      })}
    </div>
  );
}
