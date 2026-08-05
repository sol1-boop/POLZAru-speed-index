/**
 * Компоненты для отображения графиков и аналитики.
 * Использует Recharts для визуализации.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MetricData {
  date: string;
  performance: number;
  accessibility: number;
  best_practices: number;
  seo: number;
  lcp?: number;
  fid?: number;
  cls?: number;
  fcp?: number;
}

interface TrendsChartProps {
  data: MetricData[];
  title?: string;
}

export const PerformanceTrendsChart: React.FC<TrendsChartProps> = ({ data, title = "Динамика производительности" }) => {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorPerf" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleDateString()}
                formatter={(value: number) => [`${value.toFixed(1)}`, 'Score']}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="performance" 
                stroke="#8884d8" 
                fillOpacity={1} 
                fill="url(#colorPerf)" 
                name="Performance"
              />
              <Line type="monotone" dataKey="accessibility" stroke="#82ca9d" name="Accessibility" />
              <Line type="monotone" dataKey="best_practices" stroke="#ffc658" name="Best Practices" />
              <Line type="monotone" dataKey="seo" stroke="#ff7300" name="SEO" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export const CoreWebVitalsChart: React.FC<TrendsChartProps> = ({ data, title = "Core Web Vitals" }) => {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <Legend />
              <Line type="monotone" dataKey="lcp" stroke="#ff7300" name="LCP (ms)" />
              <Line type="monotone" dataKey="fid" stroke="#82ca9d" name="FID (ms)" />
              <Line type="monotone" dataKey="cls" stroke="#8884d8" name="CLS" yAxisId={1} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

interface Anomaly {
  metric: string;
  type: string;
  message: string;
}

interface AnomaliesListProps {
  anomalies: Anomaly[];
}

export const AnomaliesList: React.FC<AnomaliesListProps> = ({ anomalies }) => {
  if (anomalies.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground text-center">Аномалий не обнаружено 🎉</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-red-500">Обнаружены аномалии</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {anomalies.map((anomaly, idx) => (
            <div key={idx} className="flex items-center p-3 bg-red-50 rounded-md border border-red-200">
              <Badge variant="destructive" className="mr-2">{anomaly.metric}</Badge>
              <span className="text-sm font-medium">{anomaly.message}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
