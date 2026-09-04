"use client";

import ChannelIcon from "@/components/ChannelIcon";
import { CHANNEL_HELP, CHANNEL_LABELS } from "@/lib/friendly";

export default function ChannelStatus({ channels }) {
  return (
    <div className="channel-status">
      {channels.map((channel) => (
        <div
          key={channel.value}
          className={`channel-card ${channel.configured ? "ready" : "pending"}`}
        >
          <span className="channel-card-icon">
            <ChannelIcon channel={channel.value} size={18} />
          </span>
          <div>
            <div className="channel-card-name">
              {CHANNEL_LABELS[channel.value] || channel.label}
            </div>
            <div className="channel-card-note">
              {channel.configured ? "Connected" : "Not connected yet"}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
